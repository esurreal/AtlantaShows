import os
import subprocess
from fastapi import FastAPI
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
    # Trigger the collector on startup
    subprocess.Popen(["python", "collector.py"])

@app.get("/")
def read_root():
    db = SessionLocal()
    try:
        # Fetch all shows from the database
        events = db.query(Event).order_by(Event.date_time).all()
        return {
            "status": "Online",
            "total_events": len(events),
            "events": [
                {
                    "date": str(e.date_time),
                    "artist": e.name,
                    "venue": e.venue_name,
                    "link": e.ticket_url
                } for e in events
            ]
        }
    finally:
        db.close()