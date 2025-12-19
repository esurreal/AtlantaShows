import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# 1. Load the variables
load_dotenv()

# 2. Grab the URL from the environment
DATABASE_URL = os.getenv("DATABASE_URL")

# 3. Handle the case where it might be missing
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment variables!")

# 4. Create the engine with the 'sturdy' settings we discussed
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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