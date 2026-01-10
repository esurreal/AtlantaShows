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
        grouped_events = defaultdict(lambda: {"artists": set(), "link": "", "is_manual": False})
        unique_dropdown_venues = set()
        
        for e in raw_events:
            if e.date_time < today: continue
            
            v_display = e.venue_name
            # Dropdown Grouping
            if "Masquerade" in v_display: v_dropdown = "The Masquerade"
            elif any(x in v_display for x in ["Center Stage", "The Loft", "Vinyl"]): v_dropdown = "Center Stage / Loft / Vinyl"
            else: v_dropdown = v_display
            
            unique_dropdown_venues.add(v_dropdown)
            key = (e.date_time, v_display)
            grouped_events[key]["artists"].add(e.name)
            grouped_events[key]["link"] = e.ticket_url
            if e.tm_id.startswith("man-"): grouped_events[key]["is_manual"] = True

        venue_options = '<option value="all">All Venues</option>'
        for v in sorted(list(unique_dropdown_venues)):
            venue_options += f'<option value="{v}">{v}</option>'

        rows = ""
        for (event_date, venue), data in sorted(grouped_events.items()):
            full_lineup = " / ".join(sorted(list(data["artists"])))
            safe_id = f"{event_date.isoformat()}-{venue.replace(' ', '-').lower()}"
            filter_venue = "The Masquerade" if "Masquerade" in venue else ("Center Stage / Loft / Vinyl" if any(x in venue for x in ["Center Stage", "The Loft", "Vinyl"]) else venue)
            
            badge = '<span class="manual-badge">Verified</span>' if data["is_manual"] else ""
            
            rows += f"""
            <tr class="event-row" id="row-{safe_id}" data-date="{event_date.isoformat()}" data-venue-filter="{filter_venue}">
                <td><button class="star-btn" data-id="{safe_id}">★</button></td>
                <td class="date-cell">{event_date.strftime('%a, %b %d')}</td>
                <td class="name-cell"><strong>{full_lineup}</strong> {badge}</td>
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
                    :root {{ --bg: #121212; --text: #ffffff; --primary: #bb86fc; --gold: #fbc02d; --row-hover: #252525; --highlight-bg: #2d2a16; }}
                    body {{ font-family: -apple-system, sans-serif; margin: 0; background: var(--bg); color: var(--text); padding: 20px; }}
                    .container {{ max-width: 1000px; margin: auto; }}
                    header {{ text-align: center; padding: 20px 0; }}
                    .controls-box {{ background: #1e1e1e; padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #333; }}
                    .search-row {{ display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }}
                    input#search, select#venue-select {{ padding: 15px; background: #222; border: 1px solid #444; color: white; border-radius: 8px; font-size: 1rem; flex-grow: 1; }}
                    .filter-bar {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }}
                    .btn-group {{ display: flex; gap: 5px; }}
                    .tab-btn, .fav-toggle {{ background: #333; color: white; border: 1px solid #444; padding: 10px 15px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.9rem; }}
                    .tab-btn.active {{ background: var(--primary); color: black; }}
                    .fav-toggle.active {{ background: var(--gold); color: black; }}
                    .nav-controls {{ display: flex; align-items: center; gap: 15px; }}
                    .view-label {{ font-weight: bold; color: #00ffcc; min-width: 120px; text-align: center; }}
                    .manual-badge {{ font-size: 0.65rem; color: #bb86fc; border: 1px solid #bb86fc; padding: 1px 5px; border-radius: 4px; margin-left: 8px; vertical-align: middle; text-transform: uppercase; }}
                    table {{ width: 100%; border-collapse: collapse; }}
                    th {{ text-align: left; border-bottom: 2px solid #333; padding: 10px; color: #888; font-size: 0.8rem; }}
                    td {{ padding: 15px 10px; border-bottom: 1px solid #333; }}
                    .event-row:hover {{ background: var(--row-hover); }}
                    .is-highlighted {{ background: var(--highlight-bg) !important; border-left: 4px solid var(--gold); }}
                    .star-btn {{ background: none; border: none; color: #444; font-size: 1.5rem; cursor: pointer; }}
                    .is-highlighted .star-btn {{ color: var(--gold) !important; }}
                    .date-cell {{ color: #00ffcc; font-weight: bold; }}
                    .ticket-link {{ color: var(--primary); text-decoration: none; font-weight: bold; }}
                    .hidden {{ display: none !important; }}
                    .clear-link {{ color: #666; font-size: 0.7rem; cursor: pointer; margin-top: 10px; display: inline-block; }}
                </style>
            </head>
            <body>
                <header><h1>🤘 ATL Show Finder</h1></header>
                <div class="container">
                    <div class="controls-box">
                        <div class="search-row">
                            <input type="text" id="search" placeholder="Search bands...">
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
                                <button onclick="moveDate(-1)">←</button>
                                <span id="view-label" class="view-label"></span>
                                <button onclick="moveDate(1)">→</button>
                            </div>
                        </div>
                        <span class="clear-link" id="clear-btn">Clear All Stars</span>
                    </div>
                    <table>
                        <thead><tr><th></th><th>Date</th><th>Lineup</th><th>Venue</th><th>Link</th></tr></thead>
                        <tbody id="event-body">{rows}</tbody>
                    </table>
                </div>
                <script>
                    let currentTab = 'all', starredOnly = false, viewingDate = new Date();
                    viewingDate.setHours(0,0,0,0);

                    function runFilters() {{
                        const q = document.getElementById('search').value.toUpperCase();
                        const vSel = document.getElementById('venue-select').value;
                        document.querySelectorAll('.event-row').forEach(row => {{
                            const rDate = new Date(row.dataset.date + 'T00:00:00');
                            const txtM = row.innerText.toUpperCase().includes(q);
                            const strM = !starredOnly || row.classList.contains('is-highlighted');
                            const venM = vSel === 'all' || row.dataset.venueFilter === vSel;
                            let dateM = currentTab === 'all' || 
                                (currentTab === 'today' && rDate.toDateString() === viewingDate.toDateString()) ||
                                (currentTab === 'month' && rDate.getMonth() === viewingDate.getMonth() && rDate.getFullYear() === viewingDate.getFullYear());
                            row.style.display = (txtM && strM && venM && dateM) ? "" : "none";
                        }});
                        updateLabel();
                    }}

                    function updateLabel() {{
                        const nav = document.getElementById('nav-group'), lbl = document.getElementById('view-label');
                        if (currentTab === 'all') nav.classList.add('hidden');
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

                    document.querySelectorAll('.tab-btn').forEach(b => b.addEventListener('click', e => {{
                        document.querySelectorAll('.tab-btn').forEach(x => x.classList.remove('active'));
                        e.target.classList.add('active');
                        currentTab = e.target.dataset.filter;
                        runFilters();
                    }}));

                    document.getElementById('fav-filter').onclick = function() {{
                        starredOnly = !starredOnly; this.classList.toggle('active'); runFilters();
                    }};

                    document.getElementById('search').onkeyup = runFilters;
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
                        if(confirm("Clear all?")) {{ localStorage.removeItem('atl_stars'); location.reload(); }}
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