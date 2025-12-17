from fastapi import FastAPI, HTTPException
from typing import List
from datetime import date # 🚨 ADDED: Required for Pydantic date type 🚨
from pydantic import BaseModel, Field

# Import the necessary functions from your database file
# NOTE: The create_tables() line below is the only remaining use of it.
from database import create_tables, fetch_events 

# --- 1. Pydantic Response Model ---
# 🚨 ADDED: This class defines the exact JSON structure and handles date conversion 🚨
class EventResponse(BaseModel):
    # Field names match the JSON output you want
    id: int
    title: str = Field(..., alias="name")
    venue: str = Field(..., alias="venue_name")
    
    # Use the imported 'date' type. Pydantic will serialize this to a "YYYY-MM-DD" string.
    date: date = Field(..., alias="date_time") 
    
    imageUrl: str = Field(..., alias="ticket_url")

    class Config:
        # Crucial for Pydantic to read attributes from the SQLAlchemy ORM model
        orm_mode = True 
        # (If using Pydantic V2, use 'from_attributes = True' instead of orm_mode)

# --- 2. FastAPI App Initialization ---
app = FastAPI(title="Atlanta Shows API")

# --- 3. Startup Event Handler ---
@app.on_event("startup")
def startup_event():
    """
    Called once when the application starts.
    """
    print("Application startup: Creating database tables...")
    create_tables()
    print("Database tables created successfully.")

# --- 4. Root Route (Optional Check) ---
@app.get("/")
def read_root():
    return {"message": "Atlanta Shows API is running!"}

# --- 5. Main API Endpoint for Flutter App (Synchronous) ---
# 🚨 MODIFIED: Use the new Pydantic schema for guaranteed serialization 🚨
@app.get("/events", response_model=List[EventResponse])
def get_all_events():
    """
    Fetches all events from the database and returns the data 
    using the Pydantic response model.
    """
    try:
        # Call the synchronous fetch_events function
        # fetch_events() must return a list of SQLAlchemy ORM objects
        events_data = fetch_events() 
        
        # Pydantic will now automatically serialize the list of SQLAlchemy objects
        # using the EventResponse schema, correctly converting the date_time field.
        return events_data
    except Exception as e:
        # Log the error and return a 500 status if the fetch fails
        print(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching events.")