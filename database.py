import os
from sqlalchemy import create_engine, Column, String, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Database URL Logic
# Try to get the Railway URL; if not found, use a clean local SQLite string
raw_url = os.getenv("DATABASE_URL", "sqlite:///shows.db")

# Safety check: if raw_url is empty or None, force it to sqlite
if not raw_url or raw_url.strip() == "":
    raw_url = "sqlite:///shows.db"

# Cleanup whitespace
db_url = raw_url.strip()

# Fix for SQLAlchemy/Postgres naming compatibility (postgres:// -> postgresql://)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

print(f"DEBUG: Connecting to database type: {db_url.split(':')[0]}")

# 2. Engine and Session Setup
try:
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
except Exception as e:
    print(f"CRITICAL ERROR: Could not create engine with URL: {db_url}")
    # Last resort fallback to local sqlite so the server doesn't crash
    engine = create_engine("sqlite:///shows.db")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

# 3. The Event Model
class Event(Base):
    __tablename__ = 'events'
    tm_id = Column(String, primary_key=True)
    name = Column(String)
    date_time = Column(Date)
    venue_name = Column(String)
    ticket_url = Column(Text)

def create_tables():
    Base.metadata.create_all(bind=engine)

def fetch_events():
    db = SessionLocal()
    try:
        # Get all shows sorted by date
        events = db.query(Event).order_by(Event.date_time.asc()).all()
        
        formatted_events = []
        for e in events:
            # These keys match the 'alias' names in your EventResponse model
            # Your JavaScript is looking for these exact words
            formatted_events.append({
                "id": str(e.tm_id),
                "name": e.name,
                "venue_name": e.venue_name,
                "date_time": e.date_time,
                "ticket_url": e.ticket_url
            })
        return formatted_events
    finally:
        db.close()