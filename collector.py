import requests
import os
import sys
import traceback
from datetime import datetime
from sqlalchemy import select, update
from dotenv import load_dotenv  # Added for .env support

# Load environment variables from .env file
load_dotenv()

# 🚨 IMPORTANT: Use the synchronous components from your database.py 🚨
from database import SessionLocal, Event 

# --- Setup ---
TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")
EVENTBRITE_TOKEN = os.getenv("EVENTBRITE_TOKEN")
BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

def get_eventbrite_events():
    """Helper to fetch from Eventbrite API"""
    if not EVENTBRITE_TOKEN:
        print("--- Skipping Eventbrite: No Token Found ---")
        return []

    print("--- 2b. Fetching data from Eventbrite API... ---")
    # Note: Eventbrite uses 'categories' 103 for Music
    # The 'destination' API is better for searching by city
    url = "https://www.eventbriteapi.com/v3/destination/events/"
    params = {
        "location.address": "atlanta",
        "event_search.type": "music",
        "token": EVENTBRITE_TOKEN
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('events', [])
    except Exception as e:
        print(f"Eventbrite API Error: {e}")
        return []

def fetch_and_save_events():
    """Fetches events from multiple sources and saves them synchronously."""
    print("--- 1. Starting data collection... ---")

    if not TICKETMASTER_API_KEY:
        raise ValueError("FATAL ERROR: TICKETMASTER_API_KEY is missing!")
    
    db = SessionLocal() 
    updated_count = 0
    inserted_count = 0

    try:
        # --- SOURCE A: TICKETMASTER ---
        print("--- 2a. Fetching data from Ticketmaster API... ---")
        tm_params = {
            'apikey': TICKETMASTER_API_KEY,
            'city': 'Atlanta',
            'stateCode': 'GA',
            'segmentName': 'Music',
            'size': 100,
            'sort': 'date,asc'
        }
        tm_response = requests.get(BASE_URL, params=tm_params)
        tm_response.raise_for_status()
        tm_events = tm_response.json().get('_embedded', {}).get('events', [])

        # --- SOURCE B: EVENTBRITE ---
        eb_events = get_eventbrite_events()

        # Combine all events into one processing list
        # We store them as a list of tuples: (raw_data, source_type)
        all_events = [(e, 'TM') for e in tm_events] + [(e, 'EB') for e in eb_events]
        
        print(f"--- 3. Found {len(tm_events)} Ticketmaster and {len(eb_events)} Eventbrite events. ---")

        # 5. Process Unified Events
        for event, source in all_events:
            try:
                if source == 'TM':
                    # Ticketmaster Parsing
                    tm_id = event.get('id')
                    event_name = event.get('name')
                    date_str = event.get('dates', {}).get('start', {}).get('localDate')
                    venue = event.get('_embedded', {}).get('venues', [{}])[0]
                    venue_name = venue.get('name')
                    ticket_url = event.get('url')
                else:
                    # Eventbrite Parsing (Add 'eb_' prefix to avoid ID collisions)
                    tm_id = f"eb_{event.get('id')}"
                    event_name = event.get('name', {}).get('text')
                    # Eventbrite gives "2025-12-17T19:00:00Z", we just want the date part
                    date_str = event.get('start', {}).get('local', '').split('T')[0]
                    venue_name = "Eventbrite Venue" # See note below
                    ticket_url = event.get('url')

                # Convert to Python DATE object
                event_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None

                event_dict = {
                    "name": event_name,
                    "date_time": event_date, 
                    "venue_name": venue_name,
                    "ticket_url": ticket_url
                }

                # Upsert Logic
                stmt = select(Event).where(Event.tm_id == tm_id)
                existing_event = db.scalar(stmt)

                if existing_event:
                    db.execute(update(Event).where(Event.tm_id == tm_id).values(**event_dict))
                    updated_count += 1
                else:
                    new_event = Event(tm_id=tm_id, **event_dict)
                    db.add(new_event)
                    inserted_count += 1
                    
            except Exception as e:
                print(f"Skipping an event due to error: {e}")
                continue

        db.commit()
        print(f"--- 4. Success: Inserted {inserted_count}, Updated {updated_count}. ---")

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
        print("--- 5. Database session closed. ---")

if __name__ == "__main__":
    try:
        print(" STARTING MULTI-SOURCE COLLECTOR ")
        fetch_and_save_events() 
        print(" COLLECTOR FINISHED SUCCESSFULLY ")
    except Exception as e:
        print(f"FATAL UNCAUGHT EXCEPTION: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

