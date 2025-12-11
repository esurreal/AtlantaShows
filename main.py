from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, Event, init_db
from pydantic import BaseModel
import os

# Initialize database (ensure tables exist)
init_db()

app = FastAPI(title="Atlanta Concerts API")

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Schema for the data served to the mobile app
class EventSchema(BaseModel):
    id: int
    name: str
    date_time: datetime
    venue_name: str
    ticket_url: str

    class Config:
        from_attributes = True

@app.get("/events", response_model=list[EventSchema], summary="Get all upcoming Atlanta concerts")
def get_events(db: Session = Depends(get_db)):
    """Fetches all events currently stored in the database, sorted by date."""
    
    # Query all events, filter out past events, and sort by date
    events = db.query(Event).filter(Event.date_time >= datetime.now()).order_by(Event.date_time).all()
    
    if not events:
        raise HTTPException(status_code=404, detail="No upcoming events found.")
        
    return events

# Simple health check endpoint
@app.get("/", summary="Health Check")
def read_root():
    return {"status": "ok", "service": "Atlanta Concerts API"}