from fastapi import FastAPI, HTTPException
from typing import List
from datetime import date # Needed for date type hint
from pydantic import BaseModel, Field # Pydantic model imports

# Import the necessary functions from your database file
from database import create_tables, fetch_events 

# --- 1. Pydantic Response Model ---
class EventResponse(BaseModel):
    # 🚨 FIX 1: Explicitly define the 'id' field with its alias 🚨
    id: int = Field(..., alias="id")
    
    title: str = Field(..., alias="name")
    venue: str = Field(..., alias="venue_name")
    
    # Date field remains the same (it was already correctly aliased)
    date: date = Field(..., alias="date_time") 
    
    # 🚨 FIX 2: Explicitly define the 'imageUrl' field with its alias 🚨
    imageUrl: str = Field(..., alias="ticket_url")

    class Config:
        # Pydantic V2 configuration key
        from_attributes = True
# --- 2. FastAPI App Initialization ---
app = FastAPI(title="Atlanta Shows API")

# --- 3. Startup Event Handler ---
@app.on_event("startup")
def startup_event():
    """
    Called once when the application starts.
    """
    print("Application startup: Creating database tables...")
    # NOTE: This is fine to keep, though the collector can also handle this
    create_tables() 
    print("Database tables created successfully.")

# --- 4. Root Route (Optional Check) ---
@app.get("/")
def read_root():
    return {"message": "Atlanta Shows API is running!"}

# --- 5. Main API Endpoint for Flutter App (Synchronous) ---
# Using the corrected Pydantic model EventResponse
@app.get("/events", response_model=List[EventResponse])
def get_all_events():
    """
    Fetches all events from the database and returns the data 
    using the Pydantic response model.
    """
    try:
        # fetch_events() must return a list of SQLAlchemy ORM objects
        events_data = fetch_events() 
        
        return events_data
    except Exception as e:
        print(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching events.")