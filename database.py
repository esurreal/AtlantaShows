# database.py (or models.py, if you prefer)

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.future import select
from datetime import datetime

# --- Database Setup (Async) ---
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL environment variable not set.")
    
# Convert to async format for SQLAlchemy
async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

# Create the async engine
engine = create_async_engine(async_db_url, future=True)

# Create a session factory for async sessions
AsyncSessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

# --- Model Definition ---
Base = declarative_base()

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    tm_id = Column(String, unique=True, index=True) 
    name = Column(String, index=True)
    date_time = Column(DateTime)
    venue_name = Column(String)
    ticket_url = Column(String)
    
    # Helper to convert to dictionary for FastAPI
    def to_dict(self):
# 1. Check if the date_time field has a value
        if self.date_time:
            # 2. If it exists, format it to the ISO standard string
            date_string = self.date_time.isoformat()
        else:
            # 3. If it does not exist (is None/NULL), use None
            date_string = None
            
        return {
            "id": str(self.id),
            "title": self.name,
            "venue": self.venue_name,
            
            # --- CRITICAL FIX: Use the computed 'date_string' variable ---
            "date": date_string,
            "imageUrl": "https://via.placeholder.com/150",
        }


# --- Fetch Events Function (Async) ---
async def fetch_events():
    async with AsyncSessionLocal() as session:
        # Select all future events
        #stmt = select(Event).filter(Event.date_time >= datetime.now()).order_by(Event.date_time)
         stmt = select(Event).order_by(Event.date_time)
        
         result = await session.execute(stmt)
         events = result.scalars().all()
        
        # Return a list of dictionaries that match the Flutter Show model
         return [event.to_dict() for event in events]

# --- Init DB (Async) ---
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)