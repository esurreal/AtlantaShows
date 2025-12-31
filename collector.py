import os
import re
import json
import requests
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

# --- 2. Ticketmaster Scraper ---
def fetch_ticketmaster():
    events = []
    api_key = os.getenv("TM_API_KEY")
    if not api_key: return events
    url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={api_key}&city=Atlanta&classificationName=music&size=100"
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
    except Exception as e: print(f"TM Error: {e}")
    return events

# --- 3. The "SEO-Parser" Scraper ---
# This reads the HTML source directly to find the JSON-LD event data
def fetch_venue_html(venue_id, venue_display_name):
    found_events = []
    print(f"Parsing {venue_display_name} HTML...")
    
    url = f"https://www.bandsintown.com/v/{venue_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            print(f"!!! {venue_display_name} page blocked (Status: {response.status_code})")
            return []

        # Find the JSON-LD block in the HTML source code
        # We look for <script type="application/ld+json">...</script>
        script_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', response.text, re.DOTALL)
        
        for block in script_blocks:
            try:
                data = json.loads(block.strip())
                # Bandsintown puts a list of Event objects in one of these blocks
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    if item.get('@type') == 'Event':
                        raw_name = item.get('name', '')
                        # Skip if it's just the venue name
                        if not raw_name or raw_name.upper() == venue_display_name.upper():
                            continue
                        
                        clean_name = re.sub(r'(\s*@\s*.*|\s+at\s+.*)', '', raw_name, flags=re.I).strip()
                        date_str = item.get('startDate', '').split('T')[0]
                        event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        
                        found_events.append({
                            "tm_id": f"{venue_display_name[:2].lower()}-{event_date}-{clean_name.lower()[:5]}".replace(" ", ""),
                            "name": clean_name,
                            "date_time": event_date,
                            "venue_name": venue_display_name,
                            "ticket_url": item.get('url', url)
                        })
            except: continue
            
        print(f"{venue_display_name}: Found {len(found_events)} events via HTML parsing.")
    except Exception as e:
        print(f"Error parsing {venue_display_name}: {e}")
    return found_events

# --- 4. Sync ---
def sync_to_db(combined_list):
    if not combined_list: return 0
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    new_count = 0
    try:
        for event_data in combined_list:
            existing = db.query(Event).filter(
                and_(Event.date_time == event_data['date_time'], Event.venue_name.ilike(event_data['venue_name']))
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
    # 1. Ticketmaster
    all_shows = fetch_ticketmaster()
    
    # 2. Venues
    bit_venues = [
        {"id": "10001781", "name": "The Earl"},
        {"id": "10243412", "name": "Boggs Social"},
        {"id": "10007886", "name": "Eyedrum"},
        {"id": "11466023", "name": "Culture Shock"},
        {"id": "10001815", "name": "The Drunken Unicorn"},
        {"id": "10005523", "name": "529"} 
    ]

    # 3. HTML Parsing
    for v in bit_venues:
        all_shows.extend(fetch_venue_html(v['id'], v['name']))

    # 4. Sync
    total = sync_to_db(all_shows)
    print(f"--- Finished. Added {total} new shows to Database. ---")