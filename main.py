import os
import subprocess
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, String, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from collections import defaultdict

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
    # Run the collector once on startup
    subprocess.Popen(["python", "collector.py"])

@app.get("/", response_class=HTMLResponse)
def read_root():
    db = SessionLocal()
    try:
        raw_events = db.query(Event).order_by(Event.date_time).all()
        
        # Deduplication logic remains the same
        grouped_events = defaultdict(lambda: {"artists": set(), "link": ""})
        for e in raw_events:
            key = (e.date_time, e.venue_name)
            grouped_events[key]["artists"].add(e.name)
            grouped_events[key]["link"] = e.ticket_url

        rows = ""
        sorted_keys = sorted(grouped_events.keys(), key=lambda x: x[0])
        for date, venue in sorted_keys:
            data = grouped_events[(date, venue)]
            full_lineup = " / ".join(sorted(list(data["artists"])))
            highlight = "background-color: #fff9c4;" if "High on Fire" in full_lineup else ""
            
            rows += f"""
            <tr style="{highlight}">
                <td>{date}</td>
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
                    .container {{ max-width: 1000px; margin: 40px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
                    h1 {{ color: #1a1a1a; border-bottom: 3px solid #ffcc00; display: inline-block; }}
                    input {{ width: 100%; padding: 15px; margin: 20px 0; border: 2px solid #eee; border-radius: 8px; font-size: 16px; }}
                    table {{ width: 100%; border-collapse: collapse; }}
                    th {{ background: #1a1a1a; color: white; padding: 12px; text-align: left; }}
                    td {{ padding: 12px; border-bottom: 1px solid #eee; color: #444; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🤘 Atlanta Live Music</h1>
                    <input type="text" id="search" onkeyup="filterTable()" placeholder="Search bands or venues...">
                    <table id="eventTable">
                        <thead>
                            <tr><th>Date</th><th>Lineup</th><th>Venue</th><th>Link</th></tr>
                        </thead>
                        <tbody>{rows}</tbody>
                    </table>
                </div>
                <script>
                    function filterTable() {{
                        let input = document.getElementById("search").value.toUpperCase();
                        let rows = document.getElementById("eventTable").getElementsByTagName("tr");
                        for (let i = 1; i < rows.length; i++) {{
                            rows[i].style.display = rows[i].innerText.toUpperCase().includes(input) ? "" : "none";
                        }}
                    }}
                </script>
            </body>
        </html>
        """
    finally:
        db.close()