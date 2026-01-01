import os
import re
import json
import requests
import time
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Date, Text, and_
from sqlalchemy.orm import declarative_base, sessionmaker

# --- 1. Database Setup ---
Base = declarative_base()

class Event(Base):
    __tablename__ = 'events'
    tm_id = Column(String, primary_key=True)
    name = Column(String)
    date_time = Column(Date)
    venue_name = Column(String)
    ticket_url = Column(Text)

raw_db_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL", "sqlite:///shows.db")
if "postgres://" in raw_db_url:
    db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
else:
    db_url = raw_db_url

engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 2. GOOGLE PROXY CONFIGURATION ---
# Paste the URL you copied from Google Apps Script here
GOOGLE_PROXY_URL = "Yhttps://script.google.com/macros/s/AKfycbyYLF5BFIykPXWfZOqqWKWFCoNrrPAcKfEpxECorc4rFerI-x_SJws1h5SuRyVgtK2wmA/exec"

# --- 3. Ticketmaster Scraper ---
def fetch_ticketmaster():
    events = []
    api_key = os.getenv("TM_API_KEY")
    if not api_key: return events
    url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={api_key}&city=Atlanta&classificationName=music&size=100&sort=date,asc"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        found = data.get('_embedded', {}).get('events', [])
        for item in found:
            events.append({
                "tm_id": item['id'],
                "name": item['name'],
                "date_time": datetime.strptime(item['dates']['start']['localDate'], '%Y-%m-%d').date(),
                "venue_name": item['_embedded']['venues'][0]['name'],
                "ticket_url": item['url']
            })
        print(f"Ticketmaster: Found {len(events)} events.")
    except: pass
    return events

# --- 4. The Proxy-Based Scraper (For Small Venues) ---
def fetch_via_proxy(venue_id, venue_display_name):
    if "YOUR_DEPLOYED_WEB_APP_URL" in GOOGLE_PROXY_URL:
        print(f"!!! Skipping {venue_display_name}: GOOGLE_PROXY_URL not set.")
        return []
    
    found_events = []
    print(f"Fetching {venue_display_name} via Google Proxy...")
    
    try:
        # We call our Google Script, passing the venueId as a parameter
        proxy_request_url = f"{GOOGLE_PROXY_URL}?venueId={venue_id}"
        response = requests.get(proxy_request_url, timeout=30)
        
        if response.status_code != 200:
            print(f"!!! Proxy error for {venue_display_name} (Status {response.status_code})")
            return []
            
        data = response.json()
        for item in data:
            try:
                raw_name = item.get('name', '')
                # Filter out generic venue names
                if not raw_name or venue_display_name.upper() in raw_name.upper() and len(raw_name) < 20:
                    continue

                clean_name = re.sub(r'(\s*@\s*.*|\s+at\s+.*)', '', raw_name, flags=re.I).strip()
                date_str = item.get('datetime', '').split('T')[0]
                event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                found_events.append({
                    "tm_id": f"prx-{venue_id}-{event_date}-{clean_name[:5]}".lower().replace(" ", ""),
                    "name": clean_name,
                    "date_time": event_date,
                    "venue_name": venue_display_name,
                    "ticket_url": item.get('url', f"https://www.bandsintown.com/v/{venue_id}")
                })
            except: continue
        print(f"{venue_display_name}: Found {len(found_events)} events via Proxy.")
    except Exception as e:
        print(f"Error fetching {venue_display_name} via proxy: {e}")
    return found_events

# --- 5. Sync ---
def sync_to_db(combined_list):
    if not combined_list: return 0
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    new_count = 0
    try:
        for event_data in combined_list:
            existing = db.query(Event).filter(
                and_(Event.date_time == event_data['date_time'], Event.name == event_data['name'])
            ).first()
            if not existing:
                db.add(Event(**event_data))
                new_count += 1
        db.commit()
        db.query(Event).filter(Event.date_time < datetime.now().date()).delete()
        db.commit()
    finally:
        db.close()
    return new_count

if __name__ == "__main__":
    # 1. Fetch from Ticketmaster (Direct)
    all_shows = fetch_ticketmaster()
    
    # 2. Venues that require the Google Proxy
    small_venues = [
        {"id": "10001781", "name": "The Earl"},
        {"id": "10243412", "name": "Boggs Social"},
        {"id": "10007886", "name": "Eyedrum"},
        {"id": "10005523", "name": "529"},
        {"id": "10001815", "name": "The Drunken Unicorn"}
    ]

    # 3. Fetch from Small Venues (via Proxy)
    for v in small_venues:
        all_shows.extend(fetch_via_proxy(v['id'], v['name']))

    # 4. Save to Postgres
    total = sync_to_db(all_shows)
    print(f"--- Finished. Added {total} new shows to Database. ---")