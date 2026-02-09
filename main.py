import os
import io
import re
import json
from fastapi import FastAPI, Form, Request, Body, UploadFile, File
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

COMMON_STYLE = """
<style>
    :root { 
        --bg: #fcfcfc; --card-bg: #ffffff; --text: #444444; 
        --text-light: #888888; --primary: #007aff; --gold: #fbc02d; 
        --row-hover: #f7f7f7; --highlight-bg: #fffdeb; --border: #eeeeee; --danger: #ff3b30;
    }
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; background: var(--bg); color: var(--text); padding: 20px; line-height: 1.6; min-width: 1000px; }
    .container { max-width: 1000px; margin: auto; }
    header { text-align: center; padding: 20px 0; }
    h1 { font-family: "Baskerville", serif; font-weight: 400; font-size: 3rem; letter-spacing: 2px; color: #1a1a1a; margin: 0; text-transform: uppercase; }
    .controls-box { background: var(--card-bg); padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid var(--border); box-shadow: 0 2px 8px rgba(0,0,0,0.04); position: sticky; top: 10px; z-index: 100; }
    .search-input { height: 44px; padding: 0 12px; background: #fff; border: 1px solid #ddd; border-radius: 8px; font-size: 16px; outline: none; box-sizing: border-box; }
    .tab-btn, .fav-toggle, .admin-btn { background: #eee; color: #666; border: none; padding: 0 16px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.8rem; height: 38px; display: inline-flex; align-items: center; justify-content: center; transition: background 0.2s; }
    .tab-btn.active { background: #444; color: white; }
    .fav-toggle.active { background: var(--gold); color: #442c00; }
    .admin-btn { background: #444; color: white; margin-top: 10px; }
    .nav-row { display: flex; justify-content: center; align-items: center; gap: 15px; margin-top: 15px; padding-top: 15px; border-top: 1px solid #f0f0f0; }
    .hidden { display: none !important; }
    table { width: 100%; border-collapse: collapse; background: var(--card-bg); border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    th { text-align: left; padding: 12px; border-bottom: 2px solid #eee; color: #888; font-size: 0.7rem; text-transform: uppercase; }
    td { padding: 12px 15px; border-bottom: 1px solid var(--border); }
    .is-highlighted { background: var(--highlight-bg) !important; }
    .star-btn { background: none; border: none; color: #ccc; font-size: 1.2rem; cursor: pointer; }
    .is-highlighted .star-btn { color: var(--gold); }
    textarea { width: 100%; font-family: monospace; padding: 12px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; background: #fafafa; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
def read_root():
    db = SessionLocal()
    today = date.today()
    try:
        raw_events = db.query(Event).filter(Event.date_time >= today).order_by(Event.date_time).all()
        rows = ""
        unique_venues = set()
        for e in raw_events:
            v_filter = "The Masquerade" if "Masquerade" in e.venue_name else ("Center Stage / Loft / Vinyl" if any(x in e.venue_name for x in ["Center Stage", "The Loft", "Vinyl"]) else e.venue_name)
            unique_venues.add(v_filter)
            rows += f"""<tr class="event-row" data-date="{e.date_time.isoformat()}" data-venue="{v_filter}" data-month="{e.date_time.month-1}" data-content="{e.name.upper()}">
                <td><button class="star-btn" onclick="this.closest('tr').classList.toggle('is-highlighted')">★</button></td>
                <td style="width:110px; font-weight:700; color:#888;">{e.date_time.strftime('%a, %b %d')}</td>
                <td><strong>{e.name}</strong></td>
                <td>{e.venue_name}</td>
                <td><a href="{e.ticket_url or '#'}" target="_blank" style="color:var(--primary); font-weight:bold; text-decoration:none;">Tickets</a></td></tr>"""
        
        venue_options = f'<option value="all">All Venues</option>' + "".join([f'<option value="{v}">{v}</option>' for v in sorted(list(unique_venues))])

        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>ATL SHOWS</title>{COMMON_STYLE}</head>
            <body><header><h1>ATL SHOWS</h1></header>
                <div class="container">
                    <div class="controls-box">
                        <div style="display:flex; gap:10px; margin-bottom: 10px;">
                            <input type="text" id="search" class="search-input" placeholder="Search bands..." style="flex:1;">
                            <select id="venue-select" class="search-input" style="flex:1;">{venue_options}</select>
                        </div>
                        <div style="display:flex; gap:8px;">
                            <button class="tab-btn active" data-filter="all">ALL</button>
                            <button class="tab-btn" data-filter="month">MONTHLY</button>
                            <button class="tab-btn" data-filter="today">DAILY</button>
                            <button id="fav-filter" class="fav-toggle">STARRED</button>
                        </div>
                        <div id="nav-row" class="nav-row" style="display:none;">
                            <button class="tab-btn" onclick="moveDate(-1)">←</button>
                            <span id="view-label" style="font-weight:bold; min-width:150px; text-align:center;"></span>
                            <button class="tab-btn" onclick="moveDate(1)">→</button>
                        </div>
                    </div>
                    <table><tbody id="event-body">{rows}</tbody></table>
                </div>
                <script>
                    const allRows = Array.from(document.getElementsByClassName('event-row'));
                    let currentTab = 'all', starredOnly = false, viewingDate = new Date();
                    viewingDate.setHours(0,0,0,0);

                    function runFilters() {{
                        const q = document.getElementById('search').value.toUpperCase();
                        const vSel = document.getElementById('venue-select').value;
                        const vMonth = viewingDate.getMonth();
                        const vDayStr = viewingDate.toISOString().split('T')[0];

                        for(let i=0; i<allRows.length; i++) {{
                            const row = allRows[i];
                            const isStarred = row.classList.contains('is-highlighted');
                            const matchTxt = !q || row.dataset.content.includes(q);
                            const matchVen = vSel === 'all' || row.dataset.venue === vSel;
                            
                            let show = matchTxt && matchVen;
                            if (show) {{
                                if (starredOnly) show = isStarred;
                                else if (currentTab === 'today') show = row.dataset.date === vDayStr;
                                else if (currentTab === 'month') show = parseInt(row.dataset.month) === vMonth;
                            }}
                            row.className = show ? 'event-row' + (isStarred ? ' is-highlighted' : '') : 'event-row hidden';
                        }}
                        document.getElementById('nav-row').style.display = (currentTab === 'all' || starredOnly) ? 'none' : 'flex';
                        document.getElementById('view-label').innerText = currentTab === 'today' ? viewingDate.toLocaleDateString('en-US', {{month:'short', day:'numeric'}}) : viewingDate.toLocaleDateString('en-US', {{month:'long'}});
                    }}

                    window.moveDate = (dir) => {{ 
                        if(currentTab==='today') viewingDate.setDate(viewingDate.getDate()+dir); 
                        else viewingDate.setMonth(viewingDate.getMonth()+dir); 
                        runFilters(); 
                    }};

                    document.querySelectorAll('.tab-btn[data-filter]').forEach(b => b.addEventListener('click', (e) => {{
                        document.querySelectorAll('.tab-btn').forEach(x => x.classList.remove('active'));
                        e.target.classList.add('active'); 
                        currentTab = e.target.dataset.filter;
                        // Turn off Starred filter when switching time views
                        starredOnly = false;
                        document.getElementById('fav-filter').classList.remove('active');
                        runFilters();
                    }}));

                    document.getElementById('search').addEventListener('input', runFilters);
                    document.getElementById('venue-select').addEventListener('change', runFilters);
                    document.getElementById('fav-filter').addEventListener('click', function() {{ 
                        starredOnly = !starredOnly; this.classList.toggle('active'); runFilters(); 
                    }});

                    runFilters();
                </script></body></html>"""
    finally:
        db.close()

@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    db = SessionLocal()
    manual_shows = db.query(Event).filter(Event.tm_id.like('manual-%')).order_by(Event.date_time).all()
    unique_venues = sorted(list(set(s.venue_name for s in manual_shows)))
    db.close()
    
    venue_options = '<option value="all">All Venues</option>' + "".join([f'<option value="{v}">{v}</option>' for v in unique_venues])
    rows = "".join([f'<tr class="admin-row" data-venue="{s.venue_name}"><td><input type="checkbox" class="show-check" value="{s.tm_id}"></td><td>{s.date_time}</td><td>{s.name}</td><td>{s.venue_name}</td></tr>' for s in manual_shows])

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Admin</title>{COMMON_STYLE}</head>
    <body><div class="container">
        <header><h1>ADMIN PANEL</h1></header>
        <div class="controls-box">
            <h3>Option 2: Direct Inject (JSON)</h3>
            <textarea id="json-input" style="height:80px;"></textarea>
            <button class="admin-btn" onclick="injectJSON()" style="background:#6f42c1;">Inject Data</button>
        </div>
        
        <div class="controls-box">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                <h3 style="margin:0;">Stored Manual Shows</h3>
                <div style="display:flex; gap:10px;">
                    <select id="admin-venue-filter" class="search-input" style="height:38px;">{venue_options}</select>
                    <button class="admin-btn" style="background:var(--danger); margin:0;" onclick="deleteSelected()">Delete Selected</button>
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th><input type="checkbox" id="select-all" onclick="toggleAll(this)"></th>
                        <th>Date</th><th>Band</th><th>Venue</th>
                    </tr>
                </thead>
                <tbody id="admin-tbody">{rows}</tbody>
            </table>
            <br><a href="/" style="display:block; text-align:center;">Back to Home</a>
        </div>
    </div>
    <script>
        async function injectJSON() {{
            try {{
                const data = JSON.parse(document.getElementById('json-input').value);
                await fetch('/admin/bulk-save', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(data) }});
                location.reload();
            }} catch(e) {{ alert("Invalid JSON"); }}
        }}
        
        function toggleAll(master) {{
            const checkboxes = document.querySelectorAll('.show-check');
            checkboxes.forEach(cb => {{
                if (cb.closest('tr').style.display !== 'none') cb.checked = master.checked;
            }});
        }}

        document.getElementById('admin-venue-filter').addEventListener('change', function() {{
            const val = this.value;
            document.querySelectorAll('.admin-row').forEach(row => {{
                row.style.display = (val === 'all' || row.dataset.venue === val) ? '' : 'none';
            }});
        }});

        async function deleteSelected() {{
            const ids = Array.from(document.querySelectorAll('.show-check:checked')).map(cb => cb.value);
            if(ids.length > 0 && confirm("Delete selected?")) {{
                await fetch('/admin/delete-bulk', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(ids) }});
                location.reload();
            }}
        }}
    </script></body></html>"""

@app.post("/admin/bulk-save")
async def bulk_save(data: list = Body(...)):
    db = SessionLocal()
    current_year = 2026
    for item in data:
        try:
            ds = item['date'].strip()
            fmt = "%Y %b %d" if len(ds.split()[0]) == 3 else "%Y %B %d"
            dt = datetime.strptime(f"{current_year} {ds}", fmt)
            if dt.date() < date.today(): dt = dt.replace(year=current_year + 1)
            tm_id = f"manual-{item['name'].replace(' ', '')}-{dt.date().isoformat()}"
            db.merge(Event(tm_id=tm_id, name=item['name'], date_time=dt.date(), venue_name=item['venue']))
        except: continue
    db.commit(); db.close()
    return {"status": "ok"}

@app.post("/admin/delete-bulk")
async def delete_bulk(ids: list = Body(...)):
    db = SessionLocal()
    db.query(Event).filter(Event.tm_id.in_(ids)).delete(synchronize_session=False)
    db.commit(); db.close()
    return {"status": "ok"}