from fastapi import FastAPI, HTTPException
from typing import List

# Import the necessary functions from your database file
from .database import create_tables, fetch_events 

# --- 1. FastAPI App Initialization ---
app = FastAPI(title="Atlanta Shows API")

# --- 2. Startup Event Handler (The Fix Trigger) ---
@app.on_event("startup")
def startup_event():
    """
    Called once when the application starts. 
    This is where the new, correct 'events' table schema is applied 
    to your Railway PostgreSQL database.
    """
    print("Application startup: Creating database tables...")
    create_tables()
    print("Database tables created successfully.")

# --- 3. Root Route (Optional Check) ---
@app.get("/")
def read_root():
    return {"message": "Atlanta Shows API is running!"}

# --- 4. Main API Endpoint for Flutter App (Synchronous) ---
@app.get("/events", response_model=List[dict])
def get_all_events():
    """
    Fetches all events from the database and returns the data 
    as a list of dictionaries.
    """
    try:
        # Call the synchronous fetch_events function
        events_data = fetch_events() 
        
        return events_data
    except Exception as e:
        # Log the error and return a 500 status if the fetch fails
        print(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching events.")