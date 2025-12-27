import os
from dotenv import load_dotenv
from database import SessionLocal, Event
from scraper_earl import scrape_the_earl
import requests
from datetime import datetime

# Load environment variables
load_dotenv()

def fetch_ticketmaster_events():
    print("--- 2a. Fetching Ticketmaster... ---")
    # Using your existing TM logic here
    # (Assuming you have your TM_API_KEY in your .env)
    API_KEY = os.getenv("TICKETMASTER_API_KEY")
    url = f"https://app.ticketmaster.com/discovery/v2/events.json?classificationName=music&city=Atlanta&apikey={API_KEY}"

    try:
        r = requests.get(url)
        data = r.json()
        raw_events = data.get('_embedded', {}).get('events', [])
        
        cleaned = []
        for e in raw_events:
            cleaned.append({
                "tm_id": e['id'],
                "name": e['name'],
                "venue_name": e['_embedded']['venues'][0]['name'],
                "date_time": datetime.strptime(e['dates']['start']['localDate'], '%Y-%m-%d').date(),
                "ticket_url": e['url']
            })
        return cleaned
    except Exception as e:
        print(f"Ticketmaster Error: {e}")
        return []

def sync_to_db(all_events):
    db = SessionLocal()
    new_count = 0
    updated_count = 0
    seen_ids = set() # Track IDs in this specific run
    
    for event_data, source in all_events:
        eid = event_data['tm_id']
        
        # Skip if we already processed this ID in this current loop
        if eid in seen_ids:
            continue
        seen_ids.add(eid)

        # Look for existing event in the actual database
        existing_event = db.query(Event).filter(Event.tm_id == eid).first()
        
        if existing_event:
            existing_event.name = event_data['name']
            existing_event.venue_name = event_data['venue_name']
            existing_event.date_time = event_data['date_time']
            existing_event.ticket_url = event_data['ticket_url']
            updated_count += 1
        else:
            new_event = Event(**event_data)
            db.add(new_event)
            new_count += 1
            
    db.commit()
    db.close()
    print(f"--- 4. Final Sync: +{new_count} new, ~{updated_count} updated. ---")

if __name__ == "__main__":
    print("--- 1. Starting data collection... ---")
    
    # 1. Get Ticketmaster shows
    tm_events = fetch_ticketmaster_events()
    print(f"Fetched {len(tm_events)} Ticketmaster events.")
    
    # 2. Get The Earl shows
    print("--- 2b. Scraping The Earl (EAV)... ---")
    try:
        earl_events = scrape_the_earl()
        print(f"Scraped {len(earl_events)} shows from The Earl.")
    except Exception as e:
        print(f"Earl Scraper failed: {e}")
        earl_events = []

    # 3. Combine them
    # We create a list of tuples: (data_dict, source_label)
    combined_list = []
    for e in tm_events:
        combined_list.append((e, 'TM'))
    for e in earl_events:
        combined_list.append((e, 'DIY'))
        
    print(f"--- 3. Processing {len(combined_list)} total events. ---")
    
    # 4. Save to Database
    sync_to_db(combined_list)