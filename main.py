import os
import subprocess
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, String, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from collections import defaultdict
from datetime import date
import json

Base = declarative_base()
class Event(Base):
    __tablename__ = 'events'
    tm_id = Column(String, primary_key=True)
    name = Column(String)
    date_time = Column(Date)
    venue_name = Column(String)
    ticket_url = Column(Text)

raw_db_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL", "sqlite:///shows.db")
db_url = raw_db_url.replace("postgres://", "postgresql://", 1) if "postgres://" in raw_db_url else raw_db_url
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    if os.path.exists("collector.py"):
        subprocess.Popen(["python", "collector.py"])

@app.get("/", response_class=HTMLResponse)
def read_root():
    db = SessionLocal()
    today = date.today()
    try:
        raw_events = db.query(Event).order_by(Event.date_time).all()
        grouped_events = defaultdict(lambda: {"artists": set(), "link": ""})
        
        for e in raw_events:
            if e.date_time < today:
                continue
            
            v_norm = e.venue_name
            if "Boggs" in e.venue_name: v_norm = "Boggs Social & Supply"
            
            key = (e.date_time, v_norm)
            grouped_events[key]["artists"].add(e.name)
            grouped_events[key]["link"] = e.ticket_url

        rows = ""
        sorted_keys = sorted(grouped_events.keys(), key=lambda x: x[0])
        for event_date, venue in sorted_keys:
            data = grouped_events[(event_date, venue)]
            full_lineup = " / ".join(sorted(list(data["artists"])))
            safe_id = f"{event_date.isoformat()}-{venue.replace(' ', '-').lower()}"
            
            rows += f"""
            <tr class="event-row" 
                id="row-{safe_id}" 
                data-date="{event_date.isoformat()}"
                data-month="{event_date.month - 1}"
                data-day="{event_date.day}"
                data-year="{event_date.year}">
                <td><button class="star-btn" data-id="{safe_id}">★</button></td>
                <td class="date-cell">{event_date.strftime('%a, %b %d')}</td>
                <td class="name-cell"><strong>{full_lineup}</strong></td>
                <td class="venue-cell">{venue}</td>
                <td><a href="{data['link']}" target="_blank" class="ticket-link">Tickets</a></td>
            </tr>
            """

        return f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="UTF-8">
                <title>ATL Show Finder</title>
                <style>
                    :root {{ 
                        --bg: #121212; --text: #ffffff; --primary: #bb86fc;
                        --gold: #fbc02d; --row-hover: #252525; --highlight-bg: #2d2a16; 
                    }}
                    body {{ font-family: -apple-system, sans-serif; margin: 0; background: var(--bg); color: var(--text); padding: 20px; }}
                    .container {{ max-width: 1000px; margin: auto; }}
                    header {{ text-align: center; padding: 20px 0; }}
                    
                    .controls-box {{ background: #1e1e1e; padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #333; }}
                    
                    input#search {{ 
                        width: 100%; padding: 15px; background: #222; border: 1px solid #444; 
                        color: white; border-radius: 8px; font-size: 1rem; box-sizing: border-box; margin-bottom: 15px;
                    }}

                    .filter-bar {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }}
                    
                    .btn-group {{ display: flex; gap: 5px; }}
                    .tab-btn, .fav-toggle {{
                        background: #333; color: white; border: 1px solid #444;
                        padding: 10px 15px; border-radius: 6px; cursor: pointer;
                        font-weight: bold; transition: all 0.2s; font-size: 0.9rem;
                    }}
                    .tab-btn.active, .fav-toggle.active {{ background: var(--primary); color: black; border-color: var(--primary); }}
                    .fav-toggle.active {{ background: var(--gold); border-color: var(--gold); }}

                    .nav-controls {{ display: flex; align-items: center; gap: 15px; }}
                    .nav-arrow {{ background: #333; color: white; border: none; padding: 5px 12px; border-radius: 4px; cursor: pointer; }}
                    .view-label {{ font-weight: bold; min-width: 120px; text-align: center; color: #00ffcc; }}

                    table {{ width: 100%; border-collapse: collapse; }}
                    th {{ text-align: left; border-bottom: 2px solid #333; padding: 10px; color: #888; font-size: 0.8rem; text-transform: uppercase; }}
                    td {{ padding: 15px 10px; border-bottom: 1px solid #333; }}
                    
                    .event-row:hover {{ background: var(--row-hover); }}
                    .event-row.is-highlighted {{ background: var(--highlight-bg) !important; border-left: 4px solid var(--gold); }}
                    
                    .star-btn {{ background: none; border: none; color: #444; font-size: 1.5rem; cursor: pointer; transition: color 0.2s; }}
                    .is-highlighted .star-btn {{ color: var(--gold) !important; }}
                    
                    .date-cell {{ color: #00ffcc; font-weight: bold; white-space: nowrap; }}
                    .ticket-link {{ color: var(--primary); text-decoration: none; font-weight: bold; }}
                    
                    .hidden {{ display: none !important; }}
                    .clear-link {{ color: #666; font-size: 0.7rem; cursor: pointer; text-decoration: underline; margin-top: 10px; display: inline-block; }}
                </style>
            </head>
            <body>
                <header>
                    <h1>🤘 ATL Show Finder</h1>
                </header>

                <div class="container">
                    <div class="controls-box">
                        <input type="text" id="search" placeholder="Search bands or venues...">
                        
                        <div class="filter-bar">
                            <div class="btn-group">
                                <button class="tab-btn active" data-filter="all">ALL</button>
                                <button class="tab-btn" data-filter="month">MONTHLY</button>
                                <button class="tab-btn" data-filter="today">DAILY</button>
                                <button id="fav-filter" class="fav-toggle">STARRED ★</button>
                            </div>

                            <div id="nav-group" class="nav-controls hidden">
                                <button class="nav-arrow" id="prev-btn">←</button>
                                <span id="view-label" class="view-label"></span>
                                <button class="nav-arrow" id="next-btn">→</button>
                            </div>
                        </div>
                        <span class="clear-link" id="clear-btn">Clear All Stars</span>
                    </div>
                    
                    <table>
                        <thead>
                            <tr><th></th><th>Date</th><th>Lineup</th><th>Venue</th><th>Link</th></tr>
                        </thead>
                        <tbody id="event-body">
                            {rows}
                        </tbody>
                    </table>
                </div>

                <script>
                    let currentTab = 'all';
                    let starredOnly = false;
                    let viewingDate = new Date();
                    viewingDate.setHours(0,0,0,0);

                    // 1. Storage & Highlighting
                    function initStars() {{
                        const saved = JSON.parse(localStorage.getItem('atl_stars')) || [];
                        document.querySelectorAll('.event-row').forEach(row => {{
                            const id = row.id.replace('row-', '');
                            if (saved.includes(id)) row.classList.add('is-highlighted');
                        }});
                        runFilters();
                    }}

                    // 2. The Master Filter
                    function runFilters() {{
                        const q = document.getElementById('search').value.toUpperCase();
                        const vDay = viewingDate.getDate();
                        const vMonth = viewingDate.getMonth();
                        const vYear = viewingDate.getFullYear();

                        document.querySelectorAll('.event-row').forEach(row => {{
                            const rowDate = new Date(row.getAttribute('data-date') + 'T00:00:00');
                            
                            // Text Check
                            const textMatch = row.innerText.toUpperCase().includes(q);
                            
                            // Star Check
                            const starMatch = !starredOnly || row.classList.contains('is-highlighted');
                            
                            // Date Check
                            let dateMatch = false;
                            if (currentTab === 'all') {{
                                dateMatch = true;
                            }} else if (currentTab === 'today') {{
                                dateMatch = (rowDate.getDate() === vDay && rowDate.getMonth() === vMonth && rowDate.getFullYear() === vYear);
                            }} else if (currentTab === 'month') {{
                                dateMatch = (rowDate.getMonth() === vMonth && rowDate.getFullYear() === vYear);
                            }}

                            row.style.display = (textMatch && starMatch && dateMatch) ? "" : "none";
                        }});
                        updateLabel();
                    }}

                    function updateLabel() {{
                        const label = document.getElementById('view-label');
                        const nav = document.getElementById('nav-group');
                        
                        if (currentTab === 'all') {{
                            nav.classList.add('hidden');
                        }} else {{
                            nav.classList.remove('hidden');
                            label.innerText = (currentTab === 'today') 
                                ? viewingDate.toLocaleDateString('en-US', {{ month: 'short', day: 'numeric' }})
                                : viewingDate.toLocaleDateString('en-US', {{ month: 'long', year: 'numeric' }});
                        }}
                    }}

                    // 3. Event Listeners
                    document.querySelectorAll('.tab-btn').forEach(btn => {{
                        btn.addEventListener('click', function() {{
                            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                            this.classList.add('active');
                            currentTab = this.getAttribute('data-filter');
                            runFilters();
                        }});
                    }});

                    document.getElementById('fav-filter').addEventListener('click', function() {{
                        starredOnly = !starredOnly;
                        this.classList.toggle('active');
                        runFilters();
                    }});

                    document.getElementById('search').addEventListener('keyup', runFilters);

                    document.getElementById('prev-btn').addEventListener('click', () => moveDate(-1));
                    document.getElementById('next-btn').addEventListener('click', () => moveDate(1));

                    function moveDate(dir) {{
                        if (currentTab === 'today') viewingDate.setDate(viewingDate.getDate() + dir);
                        if (currentTab === 'month') viewingDate.setMonth(viewingDate.getMonth() + dir);
                        runFilters();
                    }}

                    document.addEventListener('click', function(e) {{
                        if (e.target.classList.contains('star-btn')) {{
                            const id = e.target.getAttribute('data-id');
                            const row = document.getElementById('row-' + id);
                            let saved = JSON.parse(localStorage.getItem('atl_stars')) || [];
                            
                            if (row.classList.toggle('is-highlighted')) {{
                                saved.push(id);
                            }} else {{
                                saved = saved.filter(i => i !== id);
                            }}
                            localStorage.setItem('atl_stars', JSON.stringify(saved));
                            runFilters();
                        }}
                    }});

                    document.getElementById('clear-btn').addEventListener('click', () => {{
                        if(confirm("Clear all stars?")) {{
                            localStorage.removeItem('atl_stars');
                            document.querySelectorAll('.event-row').forEach(r => r.classList.remove('is-highlighted'));
                            runFilters();
                        }}
                    }});

                    initStars();
                </script>
            </body>
        </html>
        """
    finally:
        db.close()