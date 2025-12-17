import requests
import os
import sys
import traceback
from datetime import datetime
from sqlalchemy import select, update

# 🚨 IMPORTANT: Use the synchronous components from your database.py 🚨
# Assuming database.py is in the same directory and contains the Event model
from database import SessionLocal, Event 

# --- Setup ---
TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")
BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

def fetch_and_save_events():
    """Fetches events from Ticketmaster and saves/updates them in the database synchronously."""
    print("--- 1. Starting Ticketmaster data collection... ---")

    # 1. Environment Check
    if not TICKETMASTER_API_KEY:
        raise ValueError("FATAL ERROR: TICKETMASTER_API_KEY is missing from environment!")
    
    # 2. API Call Setup
    params = {
        'apikey': TICKETMASTER_API_KEY,
        'city': 'Atlanta',
        'stateCode': 'GA',
        'segmentName': 'Music',
        'size': 200,
        'sort': 'date,asc'
    }

    # 3. Initialize Synchronous DB Session
    # We use the standard synchronous SessionLocal from database.py
    db = SessionLocal() 
    
    try:
        # 4. Fetch Data from Ticketmaster
        print("--- 2. Fetching data from Ticketmaster API... ---")
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
        data = response.json()
        
        events_data = data.get('_embedded', {}).get('events', [])
        print(f"--- 3. Found {len(events_data)} events to process. ---")
        
        updated_count = 0
        inserted_count = 0

        # 5. Process Events
        for event in events_data:
            tm_id = event.get('id')
            event_name = event.get('name')
            
            # --- 🌟 THE CRITICAL FIXES 🌟 ---
            
            # 5a. Extract DateTime String
            date_time_str = event.get('dates', {}).get('start', {}).get('localDateTime')
            
            # 5b. Convert to Python DATE object (required for the PostgreSQL DATE type)
            event_date = None
            if date_time_str:
                # Parse the full ISO format string (e.g., '2025-12-16T20:00:00')
                full_datetime_obj = datetime.fromisoformat(date_time_str)
                # 🚨 Take ONLY the date part to match the database schema
                event_date = full_datetime_obj.date() 
            
            # 5c. Extract Venue and URL
            venue = event.get('_embedded', {}).get('venues', [{}])[0]
            venue_name = venue.get('name')
            ticket_url = event.get('url')

            # Prepare data dictionary for insert/update
            event_dict = {
                "name": event_name,
                "date_time": event_date, 
                "venue_name": venue_name,
                "ticket_url": ticket_url
            }

            # 5d. Check if the event already exists (SQLAlchemy 2.0 style)
            # Use SELECT to check for existence
            stmt = select(Event).where(Event.tm_id == tm_id)
            existing_event = db.scalar(stmt) # scalar() returns the single result or None

            if existing_event:
                # Update existing event data
                db.execute(
                    update(Event).where(Event.tm_id == tm_id).values(**event_dict)
                )
                updated_count += 1
            else:
                # Create new event
                new_event = Event(tm_id=tm_id, **event_dict)
                db.add(new_event)
                inserted_count += 1

        # 6. Commit changes
        db.commit()
        print(f"--- 4. Success: Inserted {inserted_count} new events, Updated {updated_count} events. ---")

    except Exception as e:
        # Rollback on error
        db.rollback()
        # Re-raise the exception so the main block can catch it and log it
        raise e
        
    finally:
        # 7. Close the session
        db.close()
        print("--- 5. Database session closed. ---")

# --- Main Execution Block with Guaranteed Error Logging ---
if __name__ == "__main__":
    try:
        print("\n==============================================")
        print("  STARTING EVENT COLLECTOR (Log Guard Active) ")
        print("==============================================")
        
        fetch_and_save_events() 
        
        print("\n==============================================")
        print("    COLLECTOR FINISHED SUCCESSFULLY (No Crash)  ")
        print("==============================================")

    except Exception as e:
        # 🚨 THIS BLOCK ENSURES THE ERROR IS PRINTED TO RAILWAY LOGS 🚨
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", file=sys.stderr)
        print(f"FATAL UNCAUGHT EXCEPTION IN COLLECTOR: {e}", file=sys.stderr)
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        # Exit with a non-zero code to signal failure to Railway
        sys.exit(1)
