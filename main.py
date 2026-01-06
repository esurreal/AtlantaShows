import os
import subprocess
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, String, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- Database Setup ---
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
    # Runs the collector in the background
    subprocess.Popen(["python", "collector.py"])

@app.get("/", response_class=HTMLResponse)
def read_root():
    db = SessionLocal()
    try:
        events = db.query(Event).order_by(Event.date_time).all()
        
        # Build a simple HTML table
        rows = ""
        for e in events:
            # Highlight High on Fire rows in yellow
            bg_color = "#fff9c4" if "High on Fire" in e.name else "white"
            rows += f"""
            <tr style="background-color: {bg_color}; border-bottom: 1px solid #ddd;">
                <td style="padding: 10px;">{e.date_time}</td>
                <td style="padding: 10px;"><strong>{e.name}</strong></td>
                <td style="padding: 10px;">{e.venue_name}</td>
                <td style="padding: 10px;"><a href="{e.ticket_url}" target="_blank">Tickets</a></td>
            </tr>
            """

        return f"""
        <html>
            <head>
                <title>Atlanta Show Finder</title>
                <style>
                    body {{ font-family: sans-serif; margin: 40px; line-height: 1.6; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th {{ text-align: left; background: #333; color: white; padding: 10px; }}
                </style>
            </head>
            <body>
                <h1>🤘 Atlanta Show Calendar</h1>
                <p>Found {len(events)} upcoming events.</p>
                <table>
                    <tr>
                        <th>Date</th>
                        <th>Artist</th>
                        <th>Venue</th>
                        <th>Link</th>
                    </tr>
                    {rows}
                </table>
            </body>
        </html>
        """
    finally:
        db.close()