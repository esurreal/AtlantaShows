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
    h1 { 
        font-family: "Baskerville", serif;
        font-weight: 400; font-size: 3.5rem; letter-spacing: 2px; color: #1a1a1a; margin: 0; text-transform: uppercase;
    }
    .controls-box { background: var(--card-bg); padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid var(--border); box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    input, select, textarea, .admin-btn { padding: 12px; background: #fff; border: 1px solid #ddd; color: var(--text); border-radius: 8px; font-size: 16px; outline: none; box-sizing: border-box; }
    .admin-btn { background: #444; color: white; cursor: pointer; font-weight: bold; border: none; padding: 12px 20px; text-decoration: none; display: inline-block; }
    .admin-btn:hover { background: #222; }
    textarea { width: 100%; min-height: 200px; font-family: monospace; font-size: 14px; margin-bottom: 10px; border: 1px solid #ddd; }
    .bulk-row { display: flex; gap: 10px; margin-bottom: 8px; background: #f9f9f9; padding: 10px; border-radius: 8px; border: 1px solid #eee; }
    .bulk-row input { flex: 1; padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px; }
    .hidden { display: none !important; }
    .manage-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; margin-top: 15px; }
    .manage-table th { text-align: left; padding: 10px; border-bottom: 2px solid #eee; color: #999; text-transform: uppercase; font-size: 0.7rem; }
    .manage-table td { padding: 10px; border-bottom: 1px solid #eee; }
    .del-btn-multi { background: var(--danger); color: white; border: none; padding: 8px 15px; border-radius: 6px; cursor: pointer; font-weight: bold; }
    .del-btn-multi:disabled { background: #ccc; cursor: not-allowed; }
</style>
"""

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
                    .filter-bar {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; }}
                    .btn-group {{ display: flex; gap: 5px; }}
                    .tab-btn, .fav-toggle {{ background: #eee; color: #666; border: none; padding: 10px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.8rem; }}
                    .tab-btn.active {{ background: #444; color: white; }}
                    .fav-toggle.active {{ background: var(--gold); color: #442c00; }}
                    .view-label {{ font-weight: bold; color: var(--primary); min-width: 120px; text-align: center; }}
                    table {{ width: 100%; border-collapse: collapse; background: var(--card-bg); border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
                    th {{ text-align: left; border-bottom: 2px solid var(--border); padding: 15px; color: #999; font-size: 0.75rem; text-transform: uppercase; }}
                    td {{ padding: 16px 15px; border-bottom: 1px solid var(--border); }}
                    .event-row:hover {{ background: var(--row-hover); }}
                    .is-highlighted {{ background: var(--highlight-bg) !important; border-left: 4px solid var(--gold); }}
                    .star-btn {{ background: none; border: none; color: #eee; font-size: 1.4rem; cursor: pointer; }}
                    .is-highlighted .star-btn {{ color: var(--gold) !important; }}
                    .date-cell {{ color: #777; font-weight: 700; white-space: nowrap; width: 110px; }}
                    .lineup-cell {{ font-size: 1.05rem; color: #333; }}
                    .venue-cell {{ color: var(--text-light); font-size: 0.9rem; }}
                    .clear-link {{ color: #ccc; font-size: 0.7rem; cursor: pointer; margin-top: 10px; display: inline-block; }}
                </style></head>
            <body><header><h1>ATL Show Finder</h1></header>
                <div class="container">
                    <div class="controls-box">
                        <div class="search-row" style="display:flex; gap:10px; margin-bottom:15px;">
                            <input type="text" id="search" placeholder="Search bands or venues..." style="flex-grow:1;">
                            <select id="venue-select">{venue_options}</select>
                        </div>
                        <div class="filter-bar">
                            <div class="btn-group">
                                <button class="tab-btn active" data-filter="all">ALL</button>
                                <button class="tab-btn" data-filter="month">MONTHLY</button>
                                <button id="fav-filter" class="fav-toggle">STARRED ★</button>
                            </div>
                        </div>
                        <span class="clear-link" id="clear-btn">Clear All Stars</span>
                    </div>
                    <table><thead><tr><th></th><th>Date</th><th>Lineup</th><th>Venue</th><th>Link</th></tr></thead>
                    <tbody id="event-body">{rows}</tbody></table>
                </div>
                <script>
                    let currentTab = 'all', starredOnly = false;
                    function runFilters() {{
                        const q = document.getElementById('search').value.toUpperCase();
                        const vSel = document.getElementById('venue-select').value;
                        document.querySelectorAll('.event-row').forEach(row => {{
                            const isStarred = row.classList.contains('is-highlighted');
                            const txtM = row.innerText.toUpperCase().includes(q);
                            const venM = vSel === 'all' || row.dataset.venueFilter === vSel;
                            let showRow = starredOnly ? (isStarred && txtM && venM) : (txtM && venM);
                            row.style.display = showRow ? "" : "none";
                        }});
                    }}
                    document.getElementById('fav-filter').onclick = function() {{ starredOnly = !starredOnly; this.classList.toggle('active'); runFilters(); }};
                    document.getElementById('search').oninput = runFilters;
                    document.getElementById('venue-select').onchange = runFilters;
                    document.addEventListener('click', e => {{ if (e.target.classList.contains('star-btn')) {{ const id = e.target.dataset.id; const row = document.getElementById('row-' + id); let s = JSON.parse(localStorage.getItem('atl_stars')) || []; if (row.classList.toggle('is-highlighted')) s.push(id); else s = s.filter(i => i !== id); localStorage.setItem('atl_stars', JSON.stringify(s)); runFilters(); }} }});
                    document.getElementById('clear-btn').onclick = () => {{ if(confirm("Clear stars?")) {{ localStorage.removeItem('atl_stars'); location.reload(); }} }};
                    (JSON.parse(localStorage.getItem('atl_stars')) || []).forEach(id => {{ const r = document.getElementById('row-' + id); if (r) r.classList.add('is-highlighted'); }});
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

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Admin - ATL Show Finder</title><link rel="icon" type="image/png" href="/favicon.ico">{COMMON_STYLE}</head>
    <body><header><h1>Admin Panel</h1></header>
        <div class="container">
            <div class="controls-box">
                <h3>Bulk Paste Shows</h3>
                <p style="font-size:0.85rem; color:#666; margin-bottom:10px;">Paste AXS, Ticketmaster, or manual text (Jan 15 - Band - Venue)</p>
                <textarea id="bulk-input" placeholder="Paste AXS data here..."></textarea>
                <div style="display:flex; gap:10px;">
                    <input type="text" id="bulk-venue" placeholder="Default Venue (optional)" style="flex-grow:1;">
                    <button type="button" class="admin-btn" onclick="parseBulk()" style="background:var(--primary);">Parse Text</button>
                </div>
                <div id="preview-area" class="hidden" style="margin-top:30px;">
                    <div id="bulk-list"></div>
                    <button onclick="uploadBulk()" class="admin-btn" style="background:#28a745; width:100%; margin-top:20px;">Upload All Shows</button>
                </div>
            </div>

            <div class="controls-box">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3>Manage Manual Shows</h3>
                    <button id="bulk-del-btn" class="del-btn-multi" disabled onclick="deleteSelected()">Delete Selected</button>
                </div>
                <table class="manage-table">
                    <thead><tr>
                        <th><input type="checkbox" id="select-all" onclick="toggleSelectAll()"></th>
                        <th>Date</th><th>Band</th><th>Venue</th>
                    </tr></thead>
                    <tbody>{manage_rows}</tbody>
                </table>
            </div>
            
            <div style="text-align:center; padding-bottom:40px;">
                <a href="/" class="admin-btn" style="background:#eee; color:#666;">← Back to Site</a>
            </div>
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
                    // Find a date (e.g., Jan 15)
                    const dateMatch = line.match(/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+/i);
                    
                    if (dateMatch) {{
                        let dateStr = dateMatch[0];
                        let bandName = "";
                        let venueName = defVenue;

                        // AXS Format: Date line followed by band line, then venue line
                        if (lines[i+1] && !lines[i+1].includes(':00 PM') && !lines[i+1].match(/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/i)) {{
                            bandName = lines[i+1];
                            // Check if line i+2 is a venue (usually contains 'Atlanta' or 'GA')
                            if (lines[i+2] && (lines[i+2].includes('Atlanta') || lines[i+2].includes('GA'))) {{
                                venueName = lines[i+2].split(',')[0].replace('Heaven at ', '').replace('Hell at ', '').replace('Purgatory at ', '').trim();
                                i += 2; // Jump past band and venue lines
                            }} else {{
                                i += 1; // Jump past band line
                            }}
                        } else {{
                            // Fallback for: Jan 15 - Band Name - Venue
                            bandName = line.replace(dateStr, '').replace(/[@\\-]/g, '').trim();
                        }}

                        const div = document.createElement('div');
                        div.className = 'bulk-row';
                        div.innerHTML = `<input type="text" class="b-name" value="${{bandName}}"><input type="text" class="b-date" value="${{dateStr}}"><input type="text" class="b-venue" value="${{venueName}}"><input type="text" class="b-url" placeholder="Link">`;
                        list.appendChild(div);
                    }}
                }}
                area.classList.remove('hidden');
            }}

            async function uploadBulk() {{
                const rows = document.querySelectorAll('.bulk-row');
                const payload = Array.from(rows).map(r => ({{
                    name: r.querySelector('.b-name').value, date: r.querySelector('.b-date').value,
                    venue: r.querySelector('.b-venue').value, url: r.querySelector('.b-url').value
                }}));
                const resp = await fetch('/admin/bulk-save', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(payload) }});
                if (resp.ok) location.reload();
            }}

            function toggleSelectAll() {{
                const checked = document.getElementById('select-all').checked;
                document.querySelectorAll('.show-check').forEach(cb => cb.checked = checked);
                toggleBulkBtn();
            }}

            function toggleBulkBtn() {{
                const anyChecked = document.querySelectorAll('.show-check:checked').length > 0;
                document.getElementById('bulk-del-btn').disabled = !anyChecked;
            }}

            async function deleteSelected() {{
                const selected = Array.from(document.querySelectorAll('.show-check:checked')).map(cb => cb.value);
                if(!confirm(`Delete ${{selected.length}} shows?`)) return;
                const resp = await fetch('/admin/delete-bulk', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(selected)
                }});
                if (resp.ok) location.reload();
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
            name, raw_date, venue = item.get('name'), item.get('date'), item.get('venue')
            if "/" in raw_date: dt = datetime.strptime(f"{current_year}/{raw_date}", "%Y/%m/%d")
            else: dt = datetime.strptime(f"{current_year} {raw_date}", "%Y %b %d")
            if dt.date() < date.today(): dt = dt.replace(year=current_year + 1)
            final_date = dt.date()
            tm_id = f"manual-{name.replace(' ', '')}-{final_date.isoformat()}"
            db.merge(Event(tm_id=tm_id, name=name, date_time=final_date, venue_name=venue, ticket_url=item.get('url', '')))
        except: continue
    db.commit(); db.close()
    return {"status": "ok"}