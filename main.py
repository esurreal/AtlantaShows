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
    if os.path.exists("collector.py"):
        subprocess.Popen(["python", "collector.py"])

@app.get("/", response_class=HTMLResponse)
def read_root():
    db = SessionLocal()
    today = date.today()
    try:
        raw_events = db.query(Event).order_by(Event.date_time).all()
        grouped_events = defaultdict(lambda: {"artists": set(), "link": ""})
        unique_dropdown_venues = set()
        
        for e in raw_events:
            if e.date_time < today: continue
            
            v_display = e.venue_name
            if "Masquerade" in v_display: v_dropdown = "The Masquerade"
            elif any(x in v_display for x in ["Center Stage", "The Loft", "Vinyl"]): v_dropdown = "Center Stage / Loft / Vinyl"
            else: v_dropdown = v_display
            
            unique_dropdown_venues.add(v_dropdown)
            key = (e.date_time, v_display)
            grouped_events[key]["artists"].add(e.name)
            grouped_events[key]["link"] = e.ticket_url

        venue_options = '<option value="all">All Venues</option>'
        for v in sorted(list(unique_dropdown_venues)):
            venue_options += f'<option value="{v}">{v}</option>'

        rows = ""
        for (event_date, venue), data in sorted(grouped_events.items()):
            full_lineup = " / ".join(sorted(list(data["artists"])))
            safe_id = f"{event_date.isoformat()}-{venue.replace(' ', '-').lower()}"
            filter_venue = "The Masquerade" if "Masquerade" in venue else ("Center Stage / Loft / Vinyl" if any(x in venue for x in ["Center Stage", "The Loft", "Vinyl"]) else venue)
            
            rows += f"""
            <tr class="event-row" id="row-{safe_id}" data-date="{event_date.isoformat()}" data-venue-filter="{filter_venue}">
                <td class="star-cell"><button class="star-btn" data-id="{safe_id}">★</button></td>
                <td class="date-cell">{event_date.strftime('%a, %b %d')}</td>
                <td class="lineup-cell"><strong>{full_lineup}</strong></td>
                <td class="venue-cell">{venue}</td>
                <td class="link-cell"><a href="{data['link']}" target="_blank" class="ticket-link">Tickets</a></td>
            </tr>
            """

        return f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
                <title>🤘 ATL Show Finder</title>
                <style>
                    :root {{ 
                        --bg: #fcfcfc; 
                        --card-bg: #ffffff;
                        --text: #444444; 
                        --text-light: #888888;
                        --primary: #007aff; 
                        --gold: #fbc02d; 
                        --row-hover: #f7f7f7; 
                        --highlight-bg: #fffdeb; 
                        --border: #eeeeee;
                    }}
                    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; background: var(--bg); color: var(--text); padding: 10px; line-height: 1.4; }}
                    .container {{ max-width: 1000px; margin: auto; }}
                    header {{ text-align: center; padding: 20px 0; }}
                    h1 {{ letter-spacing: -1px; color: #222; margin: 0; font-size: 1.8rem; }}
                    
                    .controls-box {{ background: var(--card-bg); padding: 15px; border-radius: 12px; margin-bottom: 15px; border: 1px solid var(--border); box-shadow: 0 2px 8px rgba(0,0,0,0.04); }}
                    
                    .search-row {{ display: flex; gap: 10px; margin-bottom: 15px; flex-direction: column; }}
                    @media(min-width: 600px) {{ .search-row {{ flex-direction: row; }} }}

                    input#search, select#venue-select {{ 
                        padding: 12px; background: #fff; border: 1px solid #ddd; color: var(--text); 
                        border-radius: 8px; font-size: 1rem; width: 100%; box-sizing: border-box; outline: none; -webkit-appearance: none;
                    }}
                    input#search:focus {{ border-color: var(--primary); }}
                    
                    .filter-bar {{ display: flex; flex-direction: column; gap: 15px; }}
                    @media(min-width: 600px) {{ .filter-bar {{ flex-direction: row; justify-content: space-between; align-items: center; }} }}

                    .btn-group {{ display: flex; gap: 5px; flex-wrap: wrap; width: 100%; }}
                    @media(min-width: 600px) {{ .btn-group {{ width: auto; }} }}

                    .tab-btn, .fav-toggle {{ background: #eee; color: #666; border: none; padding: 10px 12px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.75rem; transition: 0.2s; flex-grow: 1; text-align: center; }}
                    @media(min-width: 600px) {{ .tab-btn, .fav-toggle {{ flex-grow: 0; padding: 10px 16px; font-size: 0.8rem; }} }}

                    .tab-btn.active {{ background: #444; color: white; }}
                    .fav-toggle.active {{ background: var(--gold); color: #442c00; }}
                    
                    .nav-controls {{ display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; }}
                    @media(min-width: 600px) {{ .nav-controls {{ width: auto; }} }}

                    .view-label {{ font-weight: bold; color: var(--primary); min-width: 100px; text-align: center; font-size: 0.9rem; }}
                    
                    .table-wrapper {{ overflow-x: auto; background: var(--card-bg); border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
                    table {{ width: 100%; border-collapse: collapse; min-width: 500px; }}
                    th {{ text-align: left; border-bottom: 2px solid var(--border); padding: 12px 10px; color: #999; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; }}
                    td {{ padding: 12px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
                    
                    .event-row:hover {{ background: var(--row-hover); }}
                    .is-highlighted {{ background: var(--highlight-bg) !important; border-left: 4px solid var(--gold); }}
                    
                    .star-cell {{ width: 30px; text-align: center; }}
                    .star-btn {{ background: none; border: none; color: #eee; font-size: 1.4rem; cursor: pointer; transition: 0.2s; padding: 0; }}
                    .is-highlighted .star-btn {{ color: var(--gold) !important; }}
                    
                    .date-cell {{ color: #777; font-weight: 700; white-space: nowrap; width: 90px; font-size: 0.85rem; }}
                    .lineup-cell {{ font-size: 0.95rem; color: #333; }}
                    .venue-cell {{ color: var(--text-light); font-size: 0.85rem; }}
                    .link-cell {{ text-align: right; }}
                    .ticket-link {{ color: var(--primary); text-decoration: none; font-weight: bold; font-size: 0.9rem; }}
                    
                    @media(max-width: 500px) {{
                        .venue-cell {{ font-size: 0.75rem; }}
                        .lineup-cell {{ font-size: 0.9rem; }}
                        td {{ padding: 10px 5px; }}
                    }}

                    .hidden {{ display: none !important; }}
                    .clear-link {{ color: #ccc; font-size: 0.7rem; cursor: pointer; margin-top: 10px; display: inline-block; text-decoration: none; text-align: center; width: 100%; }}
                </style>
            </head>
            <body>
                <header><h1>🤘 ATL Show Finder</h1></header>
                <div class="container">
                    <div class="controls-box">
                        <div class="search-row">
                            <input type="text" id="search" placeholder="Search bands or venues..." inputmode="search">
                            <select id="venue-select">{venue_options}</select>
                        </div>
                        <div class="filter-bar">
                            <div class="btn-group">
                                <button class="tab-btn active" data-filter="all">ALL</button>
                                <button class="tab-btn" data-filter="month">MONTHLY</button>
                                <button class="tab-btn" data-filter="today">DAILY</button>
                                <button id="fav-filter" class="fav-toggle">STARRED ★</button>
                            </div>
                            <div id="nav-group" class="nav-controls hidden">
                                <button class="tab-btn" onclick="moveDate(-1)">←</button>
                                <span id="view-label" class="view-label"></span>
                                <button class="tab-btn" onclick="moveDate(1)">→</button>
                            </div>
                        </div>
                        <span class="clear-link" id="clear-btn">Clear All Stars</span>
                    </div>
                    <div class="table-wrapper">
                        <table>
                            <thead><tr><th></th><th>Date</th><th>Lineup</th><th>Venue</th><th style="text-align:right">Link</th></tr></thead>
                            <tbody id="event-body">{rows}</tbody>
                        </table>
                    </div>
                </div>
                <script>
                    let currentTab = 'all', starredOnly = false, viewingDate = new Date();
                    viewingDate.setHours(0,0,0,0);

                    function runFilters() {{
                        const q = document.getElementById('search').value.toUpperCase();
                        const vSel = document.getElementById('venue-select').value;
                        
                        document.querySelectorAll('.event-row').forEach(row => {{
                            const rDate = new Date(row.dataset.date + 'T00:00:00');
                            const isStarred = row.classList.contains('is-highlighted');
                            const txtM = row.innerText.toUpperCase().includes(q);
                            const venM = vSel === 'all' || row.dataset.venueFilter === vSel;
                            
                            let showRow = false;

                            if (starredOnly) {{
                                // In Starred Mode: show if starred AND matches search/venue
                                showRow = isStarred && txtM && venM;
                            }} else {{
                                // In Regular Tabs: show if matches date AND matches search/venue
                                let dateM = currentTab === 'all' || 
                                    (currentTab === 'today' && rDate.toDateString() === viewingDate.toDateString()) ||
                                    (currentTab === 'month' && rDate.getMonth() === viewingDate.getMonth() && rDate.getFullYear() === viewingDate.getFullYear());
                                showRow = dateM && txtM && venM;
                            }}
                            
                            row.style.display = showRow ? "" : "none";
                        }});
                        updateLabel();
                    }}

                    function updateLabel() {{
                        const nav = document.getElementById('nav-group'), lbl = document.getElementById('view-label');
                        // Hide nav controls if in Starred Mode or "All" tab
                        if (currentTab === 'all' || starredOnly) nav.classList.add('hidden');
                        else {{
                            nav.classList.remove('hidden');
                            lbl.innerText = currentTab === 'today' ? viewingDate.toLocaleDateString('en-US', {{month:'short', day:'numeric'}}) : viewingDate.toLocaleDateString('en-US', {{month:'long', year:'numeric'}});
                        }}
                    }}

                    function moveDate(dir) {{
                        if (currentTab === 'today') viewingDate.setDate(viewingDate.getDate() + dir);
                        else viewingDate.setMonth(viewingDate.getMonth() + dir);
                        runFilters();
                    }}

                    // Handle Tab Buttons (All, Monthly, Daily)
                    document.querySelectorAll('.tab-btn').forEach(b => b.addEventListener('click', e => {{
                        if (!e.target.dataset.filter) return;
                        
                        // Turn OFF Starred Mode when a tab is clicked
                        starredOnly = false;
                        document.getElementById('fav-filter').classList.remove('active');
                        
                        document.querySelectorAll('.tab-btn').forEach(x => x.classList.remove('active'));
                        e.target.classList.add('active');
                        currentTab = e.target.dataset.filter;
                        runFilters();
                    }}));

                    // Handle Starred Toggle
                    document.getElementById('fav-filter').onclick = function() {{
                        starredOnly = !starredOnly;
                        this.classList.toggle('active');
                        
                        // If turning Starred ON, we visually "deactivate" the active tab highlight 
                        // but keep the currentTab variable stored for when we switch back.
                        if (starredOnly) {{
                            document.querySelectorAll('.tab-btn').forEach(x => x.classList.remove('active'));
                        }} else {{
                            // Turning Starred OFF: Restore the highlight to the active tab
                            document.querySelector(`[data-filter="${{currentTab}}"]`).classList.add('active');
                        }}
                        
                        runFilters();
                    }};

                    document.getElementById('search').oninput = runFilters;
                    document.getElementById('venue-select').onchange = runFilters;

                    document.addEventListener('click', e => {{
                        if (e.target.classList.contains('star-btn')) {{
                            const id = e.target.dataset.id;
                            const row = document.getElementById('row-' + id);
                            let s = JSON.parse(localStorage.getItem('atl_stars')) || [];
                            if (row.classList.toggle('is-highlighted')) s.push(id);
                            else s = s.filter(i => i !== id);
                            localStorage.setItem('atl_stars', JSON.stringify(s));
                            runFilters();
                        }}
                    }});

                    document.getElementById('clear-btn').onclick = () => {{
                        if(confirm("Clear all starred shows?")) {{ localStorage.removeItem('atl_stars'); location.reload(); }}
                    }};

                    (JSON.parse(localStorage.getItem('atl_stars')) || []).forEach(id => {{
                        const r = document.getElementById('row-' + id);
                        if (r) r.classList.add('is-highlighted');
                    }});
                    runFilters();
                </script>
            </body>
        </html>
        """
    finally:
        db.close()