import os
import subprocess
import json
from fastapi import FastAPI, Form, Request, Body
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy import create_engine, Column, String, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from collections import defaultdict
from datetime import date, datetime

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
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI()
FAVICON_PATH = "atlshowFavicon.png"

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    if os.path.exists(FAVICON_PATH):
        return FileResponse(FAVICON_PATH)
    return None

COMMON_STYLE = """
<style>
    :root { 
        --bg: #fcfcfc; --card-bg: #ffffff; --text: #444444; 
        --text-light: #888888; --primary: #007aff; --gold: #fbc02d; 
        --row-hover: #f7f7f7; --highlight-bg: #fffdeb; --border: #eeeeee; --danger: #ff3b30;
    }
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; background: var(--bg); color: var(--text); padding: 20px; line-height: 1.6; min-width: 1000px; }
    .container { max-width: 1000px; margin: auto; }
    header { text-align: center; padding: 40px 0 30px 0; }
    h1 { font-family: "Baskerville", serif; font-weight: 400; font-size: 3.5rem; letter-spacing: 2px; color: #1a1a1a; margin: 0; text-transform: uppercase; }
    .controls-box { background: var(--card-bg); padding: 30px; border-radius: 12px; margin-bottom: 20px; border: 1px solid var(--border); box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    
    .search-input { height: 48px; width: 100%; padding: 0 12px; background: #fff; border: 1px solid #ddd; color: var(--text); border-radius: 8px; font-size: 16px; outline: none; box-sizing: border-box; }
    
    .admin-btn { background: #444; color: white; cursor: pointer; font-weight: bold; border: none; padding: 12px 20px; text-decoration: none; display: inline-block; border-radius: 8px; }
    .admin-btn:hover { background: #222; }
    
    .clear-link { color: #444444; font-size: 0.75rem; cursor: pointer; display: inline-block; text-decoration: none; font-weight: 500; }
    .clear-link:hover { text-decoration: underline; }

    .venue-fav-btn { height: 48px; width: 48px; background: #fff; border: 1px solid #ddd; border-radius: 8px; cursor: pointer; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; }
    .hidden { display: none !important; }
    
    /* Harmonized Filter Buttons */
    .tab-btn, .fav-toggle { background: #eee; color: #666; border: none; padding: 0 16px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.8rem; height: 42px; display: inline-flex; align-items: center; justify-content: center; box-sizing: border-box; vertical-align: top; }
    .tab-btn.active { background: #444; color: white; }
    .fav-toggle.active { background: var(--gold); color: #442c00; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
def read_root():
    db = SessionLocal()
    today = date.today()
    try:
        raw_events = db.query(Event).filter(Event.date_time >= today).order_by(Event.date_time).all()
        grouped_events = defaultdict(lambda: {"artists": set(), "link": ""})
        unique_dropdown_venues = set()
        
        for e in raw_events:
            v_display = e.venue_name
            v_dropdown = "The Masquerade" if "Masquerade" in v_display else ("Center Stage / Loft / Vinyl" if any(x in v_display for x in ["Center Stage", "The Loft", "Vinyl"]) else v_display)
            unique_dropdown_venues.add(v_dropdown)
            key = (e.date_time, v_display)
            grouped_events[key]["artists"].add(e.name)
            grouped_events[key]["link"] = e.ticket_url

        venue_options = f'<option value="all">All Venues</option>' + "".join([f'<option value="{v}">{v}</option>' for v in sorted(list(unique_dropdown_venues))])
        rows = ""
        for (event_date, venue), data in sorted(grouped_events.items()):
            full_lineup = " / ".join(sorted(list(data["artists"])))
            safe_id = f"{event_date.isoformat()}-{venue.replace(' ', '-').lower()}"
            filter_v = "The Masquerade" if "Masquerade" in venue else ("Center Stage / Loft / Vinyl" if any(x in venue for x in ["Center Stage", "The Loft", "Vinyl"]) else venue)
            rows += f"""<tr class="event-row" id="row-{safe_id}" data-date="{event_date.isoformat()}" data-venue-filter="{filter_v}">
                <td><button class="star-btn" data-id="{safe_id}">★</button></td>
                <td class="date-cell">{event_date.strftime('%a, %b %d')}</td>
                <td class="lineup-cell"><strong>{full_lineup}</strong></td>
                <td class="venue-cell">{venue}</td>
                <td><a href="{data['link']}" target="_blank" style="color:var(--primary); font-weight:bold; text-decoration:none;">Tickets</a></td></tr>"""

        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=1000, user-scalable=yes">
                <title>ATL Show Finder</title><link rel="icon" type="image/png" href="/favicon.ico">{COMMON_STYLE}
                <style>
                    .view-label {{ font-weight: bold; color: var(--primary); min-width: 140px; text-align: center; }}
                    table {{ width: 100%; border-collapse: collapse; background: var(--card-bg); border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-top: 10px; }}
                    th {{ text-align: left; border-bottom: 2px solid var(--border); padding: 15px; color: #999; font-size: 0.75rem; text-transform: uppercase; }}
                    td {{ padding: 16px 15px; border-bottom: 1px solid var(--border); }}
                    .event-row:hover {{ background: var(--row-hover); }}
                    .is-highlighted {{ background: var(--highlight-bg) !important; border-left: 4px solid var(--gold); }}
                    .star-btn {{ background: none; border: none; color: #eee; font-size: 1.4rem; cursor: pointer; }}
                    .is-highlighted .star-btn {{ color: var(--gold) !important; }}
                    .date-cell {{ color: #777; font-weight: 700; white-space: nowrap; width: 110px; }}
                </style></head>
            <body><header><h1>ATL Show Finder</h1></header>
                <div class="container">
                    <div class="controls-box">
                        <div style="display:flex; gap:20px; margin-bottom: 15px;">
                            <div style="flex: 1;">
                                <input type="text" id="search" class="search-input" placeholder="Search bands...">
                            </div>
                            <div style="flex: 1; display:flex; gap:8px;">
                                <select id="venue-select" class="search-input">{venue_options}</select>
                                <button id="venue-star" class="venue-fav-btn">★</button>
                            </div>
                        </div>

                        <div style="display:flex; gap:20px; align-items: flex-start;">
                            <div style="flex: 1; display:flex; gap:5px;">
                                <button class="tab-btn active" data-filter="all">ALL</button>
                                <button class="tab-btn" data-filter="month">MONTHLY</button>
                                <button class="tab-btn" data-filter="today">DAILY</button>
                                <button id="fav-filter" class="fav-toggle">STARRED SHOWS ★</button>
                                <div id="nav-group" class="hidden" style="display:flex; align-items:center; gap:5px;">
                                    <button class="tab-btn" onclick="moveDate(-1)">←</button>
                                    <span id="view-label" class="view-label"></span>
                                    <button class="tab-btn" onclick="moveDate(1)">→</button>
                                </div>
                            </div>
                            
                            <div style="flex: 1; display:flex; flex-direction:column; gap:8px;">
                                <button id="fav-venue-filter" class="fav-toggle" style="width:100%;">FAV VENUES ★</button>
                                <span class="clear-link" style="text-align:right; cursor: default;">Click on a venue from the list and add it to your favorites</span>
                            </div>
                        </div>
                        
                        <div style="margin-top: 15px; display: flex; justify-content: space-between;">
                            <span class="clear-link" id="clear-btn">Clear All Stars</span>
                            <a href="/admin" class="clear-link" style="color: #999;">Admin Panel</a>
                        </div>
                    </div>
                    <table><thead><tr><th></th><th>Date</th><th>Lineup</th><th>Venue</th><th>Link</th></tr></thead>
                    <tbody id="event-body">{rows}</tbody></table>
                </div>
                <script>
                    let currentTab = 'all', starredOnly = false, venueFavsOnly = false;
                    let viewingDate = new Date(); viewingDate.setHours(0,0,0,0);

                    function runFilters() {{
                        const q = document.getElementById('search').value.toUpperCase();
                        const vSel = document.getElementById('venue-select').value;
                        const favVenues = JSON.parse(localStorage.getItem('atl_venue_stars')) || [];
                        
                        document.querySelectorAll('.event-row').forEach(row => {{
                            const rDate = new Date(row.dataset.date + 'T00:00:00');
                            const isStarred = row.classList.contains('is-highlighted');
                            const isFavVenue = favVenues.includes(row.dataset.venueFilter);
                            const txtM = row.innerText.toUpperCase().includes(q);
                            const venM = vSel === 'all' || row.dataset.venueFilter === vSel;
                            
                            let showRow = false;
                            let matchesSearch = txtM && venM;
                            if (venueFavsOnly) matchesSearch = matchesSearch && isFavVenue;

                            if (starredOnly) {{
                                showRow = isStarred && matchesSearch;
                            }} else if (currentTab === 'all') {{
                                showRow = matchesSearch;
                            }} else if (currentTab === 'today') {{
                                showRow = rDate.toDateString() === viewingDate.toDateString() && matchesSearch;
                            }} else if (currentTab === 'month') {{
                                showRow = rDate.getMonth() === viewingDate.getMonth() && rDate.getFullYear() === viewingDate.getFullYear() && matchesSearch;
                            }}
                            row.style.display = showRow ? "" : "none";
                        }});

                        const nav = document.getElementById('nav-group');
                        const lbl = document.getElementById('view-label');
                        if (currentTab === 'all' || starredOnly) nav.classList.add('hidden');
                        else {{
                            nav.classList.remove('hidden');
                            lbl.innerText = currentTab === 'today' ? 
                                viewingDate.toLocaleDateString('en-US', {{month:'short', day:'numeric'}}) : 
                                viewingDate.toLocaleDateString('en-US', {{month:'long', year:'numeric'}});
                        }}

                        const vStar = document.getElementById('venue-star');
                        vStar.style.color = favVenues.includes(vSel) ? "var(--gold)" : "#ddd";
                        vStar.style.display = vSel === 'all' ? "none" : "block";
                    }}

                    document.getElementById('venue-star').onclick = function() {{
                        const vSel = document.getElementById('venue-select').value;
                        if (vSel === 'all') return;
                        let favs = JSON.parse(localStorage.getItem('atl_venue_stars')) || [];
                        if (favs.includes(vSel)) favs = favs.filter(v => v !== vSel);
                        else favs.push(vSel);
                        localStorage.setItem('atl_venue_stars', JSON.stringify(favs));
                        runFilters();
                    }};

                    document.getElementById('fav-venue-filter').onclick = function() {{
                        venueFavsOnly = !venueFavsOnly;
                        this.classList.toggle('active');
                        runFilters();
                    }};

                    function moveDate(dir) {{
                        if (currentTab === 'today') viewingDate.setDate(viewingDate.getDate() + dir);
                        else viewingDate.setMonth(viewingDate.getMonth() + dir);
                        runFilters();
                    }}

                    document.querySelectorAll('.tab-btn').forEach(b => b.addEventListener('click', e => {{
                        if (!e.target.dataset.filter) return;
                        starredOnly = false;
                        venueFavsOnly = false;
                        document.getElementById('fav-filter').classList.remove('active');
                        document.getElementById('fav-venue-filter').classList.remove('active');
                        
                        document.querySelectorAll('.tab-btn').forEach(x => x.classList.remove('active'));
                        e.target.classList.add('active');
                        currentTab = e.target.dataset.filter;
                        runFilters();
                    }}));

                    document.getElementById('fav-filter').onclick = function() {{
                        starredOnly = !starredOnly;
                        this.classList.toggle('active');
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
                        if(confirm("Clear stars and venue favorites?")) {{
                            localStorage.removeItem('atl_stars');
                            localStorage.removeItem('atl_venue_stars');
                            location.reload();
                        }}
                    }};

                    (JSON.parse(localStorage.getItem('atl_stars')) || []).forEach(id => {{
                        const r = document.getElementById('row-' + id);
                        if (r) r.classList.add('is-highlighted');
                    }});
                    runFilters();
                </script></body></html>"""
    finally:
        db.close()

# --- ADMIN PANEL ROUTES ---

@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    db = SessionLocal()
    manual_shows = db.query(Event).filter(Event.tm_id.like('manual-%')).order_by(Event.date_time).all()
    db.close()

    manage_rows = ""
    for s in manual_shows:
        manage_rows += f"""<tr>
            <td><input type="checkbox" class="show-check" value="{s.tm_id}" onchange="toggleBulkBtn()"></td>
            <td>{s.date_time}</td>
            <td><strong>{s.name}</strong></td>
            <td>{s.venue_name}</td>
        </tr>"""

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Admin - ATL Show Finder</title><link rel="icon" type="image/png" href="/favicon.ico">{COMMON_STYLE}
    <style>
        .bulk-row input {{ border: 1px solid #ddd; padding: 10px; border-radius: 6px; }}
        .manage-table th, .manage-table td {{ padding: 12px; border-bottom: 1px solid #eee; }}
    </style></head>
    <body><header><h1>Admin Panel</h1></header>
        <div class="container">
            <div class="controls-box">
                <h3>Bulk Paste Shows</h3>
                <textarea id="bulk-input" placeholder="Paste AXS or list data..." style="width:100%; min-height:150px; margin-bottom:10px;"></textarea>
                <div style="display:flex; gap:10px;">
                    <input type="text" id="bulk-venue" placeholder="Default Venue" style="flex-grow:1; padding:10px; border-radius:6px; border:1px solid #ddd;">
                    <button class="admin-btn" onclick="parseBulk()" style="background:var(--primary);">Parse Text</button>
                </div>
                <div id="preview-area" class="hidden" style="margin-top:20px;">
                    <div id="bulk-list"></div>
                    <button onclick="uploadBulk()" class="admin-btn" style="background:#28a745; width:100%; margin-top:20px;">Save All</button>
                </div>
            </div>

            <div class="controls-box">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3>Manual Shows</h3>
                    <button id="bulk-del-btn" class="del-btn-multi" style="background:var(--danger); border:none; color:white; padding:8px 15px; border-radius:6px; cursor:pointer;" disabled onclick="deleteSelected()">Delete Selected</button>
                </div>
                <table class="manage-table" style="width:100%; border-collapse: collapse; margin-top:15px;">
                    <thead><tr style="text-align:left;">
                        <th><input type="checkbox" id="select-all" onclick="toggleSelectAll()"></th>
                        <th>Date</th><th>Band</th><th>Venue</th>
                    </tr></thead>
                    <tbody>{manage_rows}</tbody>
                </table>
            </div>
            <div style="text-align:center; padding:20px;"><a href="/" class="admin-btn" style="background:#eee; color:#666; text-decoration:none;">← Back</a></div>
        </div>
        <script>
            function parseBulk() {{
                const rawText = document.getElementById('bulk-input').value;
                const lines = rawText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                const list = document.getElementById('bulk-list');
                const area = document.getElementById('preview-area');
                const defVenue = document.getElementById('bulk-venue').value;
                list.innerHTML = '';

                for (let i = 0; i < lines.length; i++) {{
                    let line = lines[i];
                    const dateMatch = line.match(/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+\\d+/i);
                    if (dateMatch) {{
                        let dateStr = dateMatch[0];
                        let bandName = lines[i+1] || "Unknown Band";
                        let venueName = defVenue || "Unknown Venue";
                        const div = document.createElement('div');
                        div.className = 'bulk-row';
                        div.style = "display:flex; gap:10px; margin-bottom:5px;";
                        div.innerHTML = `<input type="text" class="b-name" value="${{bandName}}" style="flex:2"><input type="text" class="b-date" value="${{dateStr}}" style="flex:1"><input type="text" class="b-venue" value="${{venueName}}" style="flex:2">`;
                        list.appendChild(div);
                    }}
                }}
                area.classList.remove('hidden');
            }}

            async function uploadBulk() {{
                const rows = document.querySelectorAll('.bulk-row');
                const payload = Array.from(rows).map(r => ({{
                    name: r.querySelector('.b-name').value, date: r.querySelector('.b-date').value, venue: r.querySelector('.b-venue').value
                }}));
                await fetch('/admin/bulk-save', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(payload) }});
                location.reload();
            }}

            function toggleSelectAll() {{
                const checked = document.getElementById('select-all').checked;
                document.querySelectorAll('.show-check').forEach(cb => cb.checked = checked);
                toggleBulkBtn();
            }}

            function toggleBulkBtn() {{
                document.getElementById('bulk-del-btn').disabled = document.querySelectorAll('.show-check:checked').length === 0;
            }}

            async function deleteSelected() {{
                const selected = Array.from(document.querySelectorAll('.show-check:checked')).map(cb => cb.value);
                if(confirm("Delete selected?")) {{
                    await fetch('/admin/delete-bulk', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(selected) }});
                    location.reload();
                }}
            }}
        </script>
    </body></html>"""

@app.post("/admin/delete-bulk")
async def delete_bulk(ids: list = Body(...)):
    db = SessionLocal()
    db.query(Event).filter(Event.tm_id.in_(ids)).delete(synchronize_session=False)
    db.commit(); db.close()
    return {"status": "ok"}

@app.post("/admin/bulk-save")
async def bulk_save(data: list = Body(...)):
    db = SessionLocal()
    current_year = date.today().year
    for item in data:
        try:
            dt = datetime.strptime(f"{current_year} {item['date']}", "%Y %b %d")
            if dt.date() < date.today(): dt = dt.replace(year=current_year + 1)
            tm_id = f"manual-{item['name'].replace(' ', '')}-{dt.date().isoformat()}"
            db.merge(Event(tm_id=tm_id, name=item['name'], date_time=dt.date(), venue_name=item['venue']))
        except: continue
    db.commit(); db.close()
    return {"status": "ok"}