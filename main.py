import os
import subprocess
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, String, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from collections import defaultdict
from datetime import date

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
            
            rows += f"""
            <tr class="event-row" 
                data-date="{event_date.isoformat()}" 
                data-month="{event_date.month - 1}" 
                data-year="{event_date.year}">
                <td>{event_date.strftime('%a, %b %d')}</td>
                <td><strong>{full_lineup}</strong></td>
                <td>{venue}</td>
                <td><a href="{data['link']}" target="_blank">Tickets</a></td>
            </tr>
            """

        return f"""
        <html>
            <head>
                <title>ATL Show Finder</title>
                <style>
                    body {{ font-family: -apple-system, sans-serif; margin: 0; background: #f0f2f5; }}
                    .container {{ max-width: 950px; margin: 40px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
                    h1 {{ color: #1a1a1a; margin-bottom: 5px; }}
                    .subtitle {{ color: #666; margin-bottom: 20px; }}
                    
                    .controls {{ display: flex; flex-direction: column; gap: 15px; margin-bottom: 25px; }}
                    input {{ width: 100%; padding: 15px; border: 2px solid #eee; border-radius: 8px; font-size: 16px; box-sizing: border-box; }}
                    
                    .nav-bar {{ display: flex; justify-content: space-between; align-items: center; background: #f8f9fa; padding: 10px; border-radius: 8px; }}
                    .button-group {{ display: flex; gap: 8px; }}
                    .filter-btn, .nav-arrow {{ 
                        padding: 10px 16px; border: 1px solid #ddd; border-radius: 6px; background: white; 
                        color: #444; cursor: pointer; font-weight: 600; transition: all 0.2s;
                    }}
                    .filter-btn.active {{ background: #1a1a1a; color: white; border-color: #1a1a1a; }}
                    .filter-btn:hover, .nav-arrow:hover {{ background: #eee; }}
                    
                    .view-label {{ font-weight: bold; color: #1a1a1a; min-width: 150px; text-align: center; }}

                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    th {{ background: #1a1a1a; color: white; padding: 12px; text-align: left; }}
                    td {{ padding: 12px; border-bottom: 1px solid #eee; color: #444; }}
                    tr:hover {{ background-color: #f8f9fa; }}
                    a {{ color: #007bff; text-decoration: none; font-weight: bold; }}
                    
                    .hidden {{ display: none; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🤘 ATL Show Finder</h1>
                    <div class="subtitle">Upcoming Live Music Calendar</div>
                    
                    <div class="controls">
                        <input type="text" id="search" onkeyup="runFilters()" placeholder="Search bands or venues...">
                        
                        <div class="nav-bar">
                            <div class="button-group">
                                <button class="filter-btn active" onclick="setFilter('all', this)">ALL</button>
                                <button class="filter-btn" onclick="setFilter('month', this)">MONTHLY</button>
                                <button class="filter-btn" onclick="setFilter('today', this)">DAILY</button>
                            </div>
                            
                            <div id="nav-controls" class="button-group hidden">
                                <button class="nav-arrow" onclick="moveDate(-1)">←</button>
                                <span id="current-view-label" class="view-label"></span>
                                <button class="nav-arrow" onclick="moveDate(1)">→</button>
                            </div>
                        </div>
                    </div>

                    <table id="eventTable">
                        <thead>
                            <tr><th>Date</th><th>Lineup</th><th>Venue</th><th>Link</th></tr>
                        </thead>
                        <tbody>{rows}</tbody>
                    </table>
                </div>

                <script>
                    let currentFilter = 'all';
                    let viewingDate = new Date();
                    viewingDate.setHours(0,0,0,0);

                    function setFilter(filter, btn) {{
                        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                        btn.classList.add('active');
                        
                        currentFilter = filter;
                        const nav = document.getElementById('nav-controls');
                        
                        if (filter === 'all') {{
                            nav.classList.add('hidden');
                        }} else {{
                            nav.classList.remove('hidden');
                            updateLabel();
                        }}
                        runFilters();
                    }}

                    function moveDate(direction) {{
                        if (currentFilter === 'today') {{
                            viewingDate.setDate(viewingDate.getDate() + direction);
                        }} else if (currentFilter === 'month') {{
                            viewingDate.setMonth(viewingDate.getMonth() + direction);
                        }}
                        updateLabel();
                        runFilters();
                    }}

                    function updateLabel() {{
                        const label = document.getElementById('current-view-label');
                        if (currentFilter === 'today') {{
                            label.innerText = viewingDate.toLocaleDateString('en-US', {{ month: 'short', day: 'numeric', year: 'numeric' }});
                        }} else if (currentFilter === 'month') {{
                            label.innerText = viewingDate.toLocaleDateString('en-US', {{ month: 'long', year: 'numeric' }});
                        }}
                    }}

                    function runFilters() {{
                        const searchTerm = document.getElementById("search").value.toUpperCase();
                        const rows = document.querySelectorAll(".event-row");
                        
                        const vDay = viewingDate.getDate();
                        const vMonth = viewingDate.getMonth();
                        const vYear = viewingDate.getFullYear();

                        rows.forEach(row => {{
                            const rowDateStr = row.getAttribute('data-date');
                            const rowDate = new Date(rowDateStr + 'T00:00:00');
                            const textMatch = row.innerText.toUpperCase().includes(searchTerm);
                            
                            let filterMatch = false;
                            if (currentFilter === 'all') {{
                                filterMatch = true;
                            }} else if (currentFilter === 'today') {{
                                filterMatch = (rowDate.getDate() === vDay && rowDate.getMonth() === vMonth && rowDate.getFullYear() === vYear);
                            }} else if (currentFilter === 'month') {{
                                filterMatch = (rowDate.getMonth() === vMonth && rowDate.getFullYear() === vYear);
                            }}

                            row.style.display = (textMatch && filterMatch) ? "" : "none";
                        }});
                    }}
                </script>
            </body>
        </html>
        """
    finally:
        db.close()