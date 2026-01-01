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
# IMPORTANT: PASTE YOUR NEW DEPLOYMENT URL HERE
GOOGLE_PROXY_URL = "https://script.google.com/macros/s/AKfycbwTZFtCNowmREf3JH8tdiclejYi0m5wkORlfG8syXvqM8ZSsM3RL8ehLpgyGfizrMPbuw/exec"

# --- 3. Ticketmaster Scraper ---
def fetch_ticketmaster():
    events = []
    api_key = os.getenv("TM_API_KEY")
    if not api_key: 
        print("[-] Ticketmaster: No TM_API_KEY found in Railway variables.")
        return events
    url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={api_key}&city=Atlanta&classificationName=music&size=100&sort=date,asc"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        found = data.get('_embedded', {}).get('events', [])
        for item in found:
            events.append({
                "tm_id": str(item['id']),
                "name": item['name'],
                "date_time": datetime.strptime(item['dates']['start']['localDate'], '%Y-%m-%d').date(),
                "venue_name": item['_embedded']['venues'][0]['name'],
                "ticket_url": item['url']
            })
        print(f"[+] Ticketmaster: Found {len(events)} events.")
    except Exception as e:
        print(f"[!] Ticketmaster Error: {e}")
    return events

# --- 4. The Proxy Scraper ---
def fetch_via_proxy(venue_id, venue_display_name):
    if "YOUR_NEW_DEPLOYED" in GOOGLE_PROXY_URL or not GOOGLE_PROXY_URL:
        print(f"[-] Skipping {venue_display_name}: Proxy URL not configured.")
        return []
    
    found_events = []
    print(f"[*] Fetching {venue_display_name} via Proxy...")
    try:
        response = requests.get(f"{GOOGLE_PROXY_URL}?venueId={venue_id}", timeout=30)
        
        # Check if the response is actually JSON
        try:
            data = response.json()
        except Exception:
            print(f"[!] Proxy for {venue_display_name} returned HTML/Text instead of JSON. Check Google Script permissions.")
            return []

        if isinstance(data, dict) and "error" in data:
            print(f"[!] Google Script logic error: {data['error']}")
            return []

        for item in data:
            try:
                raw_name = item.get('name', '')
                if not raw_name or (venue_display_name.upper() in raw_name.upper() and len(raw_name) < 20):
                    continue

                clean_name = re.sub(r'(\s*@\s*.*|\s+at\s+.*)', '', raw_name, flags=re.I).strip()
                date_str = item.get('datetime', '').split('T')[0]
                event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                unique_id = f"prx-{venue_id}-{date_str}-{clean_name[:10]}".lower()
                unique_id = re.sub(r'[^a-z0-9-]', '', unique_id)

                found_events.append({
                    "tm_id": unique_id,
                    "name": clean_name,
                    "date_time": event_date,
                    "venue_name": venue_display_name,
                    "ticket_url": item.get('url', f"https://www.bandsintown.com/v/{venue_id}")
                })
            except: continue
        print(f"[+] {venue_display_name}: Found {len(found_events)} events.")
    except Exception as e:
        print(f"[!] Proxy Connection Failed: {e}")
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
                and_(
                    Event.date_time == event_data['date_time'],
                    Event.venue_name == event_data['venue_name']
                )
            ).first()
            if not existing:
                db.add(Event(**event_data))
                new_count += 1
        db.commit()
        db.query(Event).filter(Event.date_time < datetime.now().date()).delete()
        db.commit()
    except Exception as e:
        print(f"[!] DB Error: {e}")
        db.rollback()
    finally:
        db.close()
    return new_count

if __name__ == "__main__":
    print("--- Collection Started ---")
    all_shows = fetch_ticketmaster()
    
    small_venues = [
        {"id": "10001781", "name": "The Earl"},
        {"id": "10243412", "name": "Boggs Social"},
        {"id": "10005523", "name": "529"},
        {"id": "10001815", "name": "The Drunken Unicorn"}
    ]

    for v in small_venues:
        all_shows.extend(fetch_via_proxy(v['id'], v['name']))

    total = sync_to_db(all_shows)
    print(f"--- Finished. Added {total} new shows. ---")