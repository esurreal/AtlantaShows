from fastapi import FastAPI, HTTPException
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Import the necessary functions from your database file
from database import create_tables, fetch_events 

# --- 1. Pydantic Response Model ---
class EventResponse(BaseModel):
    event_id: str = Field(..., alias="id")
    event_title: str = Field(..., alias="name")
    event_venue: str = Field(..., alias="venue_name")
    event_date: Optional[str] = Field(None, alias="date_time") 
    event_image_url: str = Field(..., alias="ticket_url")

    @field_validator("event_date", mode="before")
    @classmethod
    def format_date(cls, v):
        # Now that 'datetime' is imported, this check will work!
        if isinstance(v, (date, datetime)):
            return v.strftime("%Y-%m-%d")
        return v

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

# --- 2. FastAPI App Initialization ---
app = FastAPI(title="Atlanta Shows API")

# Mount the static folder so CSS/JS/Images work
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 3. Routes ---

@app.get("/")
def read_index():
    return FileResponse(os.path.join('static', 'index.html'))

# The Data API used by your website/app
@app.get("/events", response_model=List[EventResponse], response_model_by_alias=True)
def get_all_events():
    try:
        events_data = fetch_events() 
        print(f"API is sending {len(events_data)} events to the frontend.")
        return events_data
    except Exception as e:
        print(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail="Error fetching events.")

@app.on_event("startup")
def startup_event():
    print("Application startup: Checking database tables...")
    create_tables()