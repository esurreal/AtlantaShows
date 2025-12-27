import os
from sqlalchemy import create_engine, Column, String, Date, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Database URL Logic
# Railway automatically provides DATABASE_URL to your app
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///shows.db")

# Fix for SQLAlchemy/Postgres naming compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 2. Engine and Session Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 3. The Event Model
# Must match the structure in collector.py
class Event(Base):
    __tablename__ = 'events'
    # Since Bandsintown/TM IDs are strings, we use String for the ID
    tm_id = Column(String, primary_key=True)
    name = Column(String)
    date_time = Column(Date)
    venue_name = Column(String)
    ticket_url = Column(Text)

# 4. Functions used by main.py
def create_tables():
    Base.metadata.create_all(bind=engine)

def fetch_events():
    db = SessionLocal()
    try:
        # Fetch all events ordered by date
        events = db.query(Event).order_by(Event.date_time.asc()).all()
        
        # Convert SQLAlchemy objects to dictionaries for the FastAPI response model
        # Note: We map 'tm_id' to 'id' so it matches your EventResponse alias
        result = []
        for e in events:
            result.append({
                "id": e.tm_id,
                "name": e.name,
                "venue_name": e.venue_name,
                "date_time": e.date_time,
                "ticket_url": e.ticket_url
            })
        return result
    finally:
        db.close()