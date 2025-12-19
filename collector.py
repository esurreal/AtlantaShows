import requests
import os
import sys
import traceback
from datetime import datetime
from sqlalchemy import select, update
from dotenv import load_dotenv 

# 1. Correct Import (No .py)
from scraper_earl import scrape_the_earl 
from database import SessionLocal, Event 

load_dotenv()

TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")
EVENTBRITE_TOKEN = os.getenv("EVENTBRITE_TOKEN")
BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

def get_eventbrite_events():
    """Helper to fetch from Eventbrite API"""
    if not EVENTBRITE_TOKEN:
        return []
    print("--- 2b. Fetching data from Eventbrite API... ---")
    url = "https://www.eventbriteapi.com/v3/destination/events/"
    headers = {"Authorization": f"Bearer {EVENTBRITE_TOKEN}"}
    params = {"event_search.type": "music", "location.address": "atlanta", "expand": "venue"}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get('events', [])
    except Exception as e:
        print(f"Eventbrite API Error: {e}")
        return []

def fetch_and_save_events():
    print("--- 1. Starting data collection... ---")
    if not TICKETMASTER_API_KEY:
        raise ValueError("FATAL ERROR: TICKETMASTER_API_KEY is missing!")
    
    db = SessionLocal() 
    updated_count = 0
    inserted_count = 0

    try:
        # --- FETCH ALL SOURCES ---
        # TM
        print("--- 2a. Fetching Ticketmaster... ---")
        tm_params = {'apikey': TICKETMASTER_API_KEY, 'city': 'Atlanta', 'segmentName': 'Music', 'size': 50}
        tm_response = requests.get(BASE_URL, params=tm_params)
        tm_events = tm_response.json().get('_embedded', {}).get('events', [])

        # EB
        eb_events = get_eventbrite_events()

        # DIY (The Earl)
        earl_events = scrape_the_earl()

        # --- COMBINE SOURCES (Corrected Logic) ---
        all_events = (
            [(e, 'TM') for e in tm_events] + 
            [(e, 'EB') for e in eb_events] + 
            [(e, 'DIY') for e in earl_events]
        )
        
        print(f"--- 3. Processing {len(all_events)} total events. ---")

        for event, source in all_events:
            try:
                if source == 'TM':
                    tm_id = event.get('id')
                    event_name = event.get('name')
                    date_str = event.get('dates', {}).get('start', {}).get('localDate')
                    venue_name = event.get('_embedded', {}).get('venues', [{}])[0].get('name')
                    ticket_url = event.get('url')
                
                elif source == 'EB':
                    tm_id = f"eb_{event.get('id')}"
                    event_name = event.get('name', {}).get('text')
                    date_str = event.get('start', {}).get('local', '').split('T')[0]
                    venue_name = "Eventbrite Venue"
                    ticket_url = event.get('url')
                
                else: # source == 'DIY' (The Earl)
                    tm_id = event.get('tm_id') # We already set this in scraper_earl.py
                    event_name = event.get('name')
                    event_date = event.get('date_time') # It's already a date object!
                    venue_name = event.get('venue_name')
                    ticket_url = event.get('ticket_url')
                    # Skip the string conversion for DIY since we did it in the scraper
                    date_str = None 

                # Convert date if it hasn't been converted yet
                if source != 'DIY' and date_str:
                    event_date = datetime.strptime(date_str, '%Y-%m-%d').date()

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
                print(f"Skipping event {source}: {e}")
                continue

        db.commit()
        print(f"--- 4. Final Sync: +{inserted_count} new, ~{updated_count} updated. ---")

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    fetch_and_save_events()