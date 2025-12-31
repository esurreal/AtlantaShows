import os
import re
import json
import requests
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Date, Text, and_
from sqlalchemy.orm import declarative_base, sessionmaker
from playwright.sync_api import sync_playwright

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

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 2. Ticketmaster Scraper ---
def fetch_ticketmaster():
    events = []
    api_key = os.getenv("TM_API_KEY")
    if not api_key: return events

    url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={api_key}&city=Atlanta&classificationName=music&size=50"
    try:
        response = requests.get(url)
        data = response.json()
        for item in data.get('_embedded', {}).get('events', []):
            events.append({
                "tm_id": item['id'],
                "name": item['name'],
                "date_time": datetime.strptime(item['dates']['start']['localDate'], '%Y-%m-%d').date(),
                "venue_name": item['_embedded']['venues'][0]['name'],
                "ticket_url": item['url']
            })
    except: pass
    return events

# --- 3. Modular Bandsintown Scraper ---
def scrape_bandsintown_venue(page, venue_id, venue_display_name):
    found_events = []
    url = f"https://www.bandsintown.com/v/{venue_id}"
    print(f"Scraping {venue_display_name}...")
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000) # Give JS time to load the calendar
        
        scripts = page.locator('script').all()
        for script in scripts:
            content = script.evaluate("node => node.textContent").strip()
            if '"startDate"' not in content: continue
            
            try:
                content = re.sub(r'^\s*//<!\[CDATA\[|//\]\]>\s*$', '', content)
                data = json.loads(content)
                
                to_check = []
                if isinstance(data, dict):
                    if "@graph" in data: to_check.extend(data["@graph"])
                    else: to_check.append(data)
                elif isinstance(data, list):
                    to_check.extend(data)

                for item in to_check:
                    if isinstance(item, dict) and 'name' in item and 'startDate' in item:
                        raw_name = item.get('name', '')
                        if not raw_name or raw_name.upper() in [venue_display_name.upper(), "BANDSINTOWN"]:
                            continue
                            
                        # Clean the name (remove venue suffixes)
                        clean_name = re.sub(r'(\s*@\s*.*|\s+at\s+.*)', '', raw_name, flags=re.I).strip()
                        start_str = item.get('startDate', '').split('T')[0]
                        
                        event_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                        event_id = f"{venue_display_name[:3].lower()}-{event_date}-{clean_name.lower()[:8]}".replace(" ", "")
                        
                        found_events.append({
                            "tm_id": event_id,
                            "name": clean_name,
                            "date_time": event_date,
                            "venue_name": venue_display_name,
                            "ticket_url": item.get('url', url)
                        })
            except: continue
    except Exception as e:
        print(f"Error scraping {venue_display_name}: {e}")
    
    return found_events

# --- 4. Sync & Cleanup ---
def sync_to_db(combined_list):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    new_count = 0
    try:
        for event_data in combined_list:
            existing = db.query(Event).filter(
                and_(
                    Event.date_time == event_data['date_time'],
                    Event.venue_name.ilike(event_data['venue_name'])
                )
            ).first()

            if not existing:
                db.add(Event(**event_data))
                new_count += 1
        db.commit()
        
        # Cleanup past shows
        today = datetime.now().date()
        db.query(Event).filter(Event.date_time < today).delete()
        db.commit()
    finally:
        db.close()
    return new_count

# --- Main Execution ---
if __name__ == "__main__":
    all_shows = fetch_ticketmaster()
    print(f"Fetched {len(all_shows)} Ticketmaster events.")

    venues = [
        {"id": "10001781", "name": "The Earl"},
        {"id": "10243412", "name": "Boggs Social"},
        {"id": "10001815", "name": "Drunken Unicorn"},
        {"id": "10007886", "name": "Eyedrum"},
        {"id": "11466023", "name": "Culture Shock"}
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        page = context.new_page()
        
        for v in venues:
            venue_shows = scrape_bandsintown_venue(page, v['id'], v['name'])
            all_shows.extend(venue_shows)
        
        browser.close()

    total = sync_to_db(all_shows)
    print(f"--- Finished. Total new shows added: {total} ---")