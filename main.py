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

# Attempt to import OCR libraries
try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None

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

# ... [Keep your existing styles and root route from previous versions] ...

@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    db = SessionLocal()
    manual_shows = db.query(Event).filter(Event.tm_id.like('manual-%')).order_by(Event.date_time).all()
    db.close()
    
    rows = "".join([f'<tr><td><input type="checkbox" class="show-check" value="{s.tm_id}" onchange="toggleBulkBtn()"></td><td>{s.date_time}</td><td><strong>{s.name}</strong></td><td>{s.venue_name}</td></tr>' for s in manual_shows])

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Admin - ATL Show Finder</title>{COMMON_STYLE}</head>
    <body><header><h1>Admin Panel</h1></header>
        <div class="container">
            <div class="controls-box">
                <h3>Universal Import</h3>
                <div id="drop-zone" class="drop-zone">Drop Screenshot Here or Paste Text Below</div>
                <input type="file" id="file-input" class="hidden" accept="image/*">
                
                <textarea id="bulk-input" placeholder="Paste 529, Culture Shock, or AXS lists here..." style="width:100%; min-height:200px; margin-top:10px; font-family:monospace;"></textarea>
                <div style="display:flex; gap:10px; margin-top:10px;">
                    <input type="text" id="bulk-venue" placeholder="Default Venue" style="flex:1; padding:10px; border-radius:6px; border:1px solid #ddd;">
                    <button class="admin-btn" onclick="parseBulk()" style="background:var(--primary);">Parse Content</button>
                </div>
                
                <div id="preview-area" class="hidden" style="margin-top:20px; border-top: 2px solid #eee; padding-top: 20px;">
                    <div id="bulk-list"></div>
                    <button onclick="uploadBulk()" class="admin-btn" style="background:#28a745; width:100%; margin-top:20px;">Save All to Database</button>
                </div>
            </div>
            
            <div class="controls-box">
                <div style="display:flex; justify-content:space-between;"><h3>Stored Manual Shows</h3><button id="bulk-del-btn" class="admin-btn" style="background:var(--danger);" disabled onclick="deleteSelected()">Delete Selected</button></div>
                <table style="width:100%; border-collapse:collapse; margin-top:15px;">
                    <thead><tr style="text-align:left;"><th><input type="checkbox" onclick="toggleSelectAll(this)"></th><th>Date</th><th>Band</th><th>Venue</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </div>

        <script>
            // ... [Keep DropZone logic] ...

            function parseBulk() {{
                const raw = document.getElementById('bulk-input').value;
                const defVenue = document.getElementById('bulk-venue').value;
                const list = document.getElementById('bulk-list');
                list.innerHTML = '';
                const lines = raw.split('\\n').map(l => l.trim()).filter(l => l.length > 0);

                let detected = [];

                for (let i = 0; i < lines.length; i++) {{
                    let line = lines[i];

                    // 1. Check for 529 Style (Band Name first, then "Day, Mon DD, YYYY")
                    if (i + 1 < lines.length && lines[i+1].match(/^(Mon|Tue|Wed|Thu|Fri|Sat|Sun),\\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/i)) {{
                        const band = line.replace('@ 529', '').trim();
                        const dateParts = lines[i+1].split('|')[0].split(',');
                        const dateStr = dateParts[1].trim() + " " + dateParts[2].trim(); // "Feb 07 2026"
                        const venue = defVenue || "529";
                        detected.push({{band, dateStr, venue}});
                        i += 1; // Skip the date line
                        continue;
                    }}

                    // 2. Check for Culture Shock Style (Day first, then Time, then Band)
                    if (line.match(/^(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY),/i)) {{
                        const dateStr = line.split(',')[1].trim(); // "JANUARY 24"
                        let band = "Unknown";
                        if (lines[i+2] && !lines[i+2].includes('TICKETS')) {{
                             band = lines[i+2];
                             i += 2;
                        }} else if (lines[i+1]) {{
                             band = lines[i+1];
                             i += 1;
                        }}
                        detected.push({{band, dateStr, venue: defVenue || "Culture Shock"}});
                        continue;
                    }}

                    // 3. Simple Fallback (Date Band Venue on one line)
                    const simpleDate = line.match(/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+\\d+/i);
                    if (simpleDate) {{
                        detected.push({{band: "Review Name", dateStr: simpleDate[0], venue: defVenue || "Unknown"}});
                    }}
                }}

                detected.forEach(item => addPreviewRow(item.band, item.dateStr, item.venue));
                if (detected.length > 0) document.getElementById('preview-area').classList.remove('hidden');
            }}

            function addPreviewRow(band, dateStr, venue) {{
                const div = document.createElement('div');
                div.className = 'bulk-row'; div.style = "display:flex; gap:10px; margin-bottom:10px; padding: 10px; background: #f9f9f9; border-radius: 6px; border: 1px solid #eee;";
                div.innerHTML = `
                    <input type="text" class="b-name" value="${{band}}" style="flex:2; padding:8px; border: 1px solid #ddd; border-radius:4px;">
                    <input type="text" class="b-date" value="${{dateStr}}" style="flex:1; padding:8px; border: 1px solid #ddd; border-radius:4px;">
                    <input type="text" class="b-venue" value="${{venue}}" style="flex:2; padding:8px; border: 1px solid #ddd; border-radius:4px;">
                `;
                document.getElementById('bulk-list').appendChild(div);
            }}

            async function uploadBulk() {{
                const payload = Array.from(document.querySelectorAll('.bulk-row')).map(r => ({{
                    name: r.querySelector('.b-name').value, 
                    date: r.querySelector('.b-date').value, 
                    venue: r.querySelector('.b-venue').value
                }}));
                await fetch('/admin/bulk-save', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(payload) }});
                location.reload();
            }}

            // ... [Keep other admin utility functions] ...
        </script>
    </body></html>"""

@app.post("/admin/bulk-save")
async def bulk_save(data: list = Body(...)):
    db = SessionLocal()
    current_year = 2026
    for item in data:
        try:
            # Flexible date parsing for "Feb 07 2026" or "JANUARY 24"
            ds = item['date'].strip()
            if re.search(r'\\d{{4}}', ds):
                dt = datetime.strptime(ds, "%b %d %Y")
            else:
                dt = datetime.strptime(f"{current_year} {ds}", "%Y %B %d")
            
            if dt.date() < date.today() and not re.search(r'\\d{{4}}', ds):
                dt = dt.replace(year=current_year + 1)
            
            tm_id = f"manual-{item['name'].replace(' ', '')}-{dt.date().isoformat()}"
            db.merge(Event(tm_id=tm_id, name=item['name'], date_time=dt.date(), venue_name=item['venue']))
        except Exception as e:
            continue
    db.commit(); db.close()
    return {"status": "ok"}