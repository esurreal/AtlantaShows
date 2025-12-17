import os
from sqlalchemy import create_engine, Column, Integer, String, Date, select
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from datetime import datetime

# --- Database Setup (Synchronous) ---
db_url = os.getenv("DATABASE_URL")
if not db_url:
    # IMPORTANT: Ensure your Railway environment variable is correctly named DATABASE_URL
    raise RuntimeError("DATABASE_URL environment variable not set.")
    
# Create the synchronous engine
engine = create_engine(db_url) 

# Create a session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# --- Model Definition ---
Base = declarative_base()

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    tm_id = Column(String, unique=True, index=True) 
    name = Column(String, index=True)
    
    # 🌟 THE CRITICAL FIX: PostgreSQL DATE type 🌟
    date_time = Column(Date) 
    
    venue_name = Column(String)
    ticket_url = Column(String)
    
def create_tables():
    """Creates the tables defined in Base.metadata (the 'events' table)."""
    Base.metadata.create_all(bind=engine)

# --- Data Fetch Function (Synchronous) ---
def fetch_events():
    """Connects to DB, retrieves all events, and closes the connection."""
    db = SessionLocal() # Get a new session
    try:
        # Build the query statement
        stmt = select(Event).order_by(Event.date_time)
        
        # Execute the query on the synchronous session
        result = db.execute(stmt)
        
        # Extract the Event objects
        events = result.scalars().all()
        
        # Convert to the list of dictionaries for the API response
        return events
    finally:
        db.close()