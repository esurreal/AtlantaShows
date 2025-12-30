import os
import re
import json
import requests
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Date, Text
from sqlalchemy.orm import declarative_base, sessionmaker # Updated Import
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

# DATABASE LOGIC
raw_db_url = os.getenv("DATABASE_URL", "sqlite:///shows.db")
if "postgres.railway.internal" in raw_db_url:
    public_url = os.getenv("DATABASE_PUBLIC_URL")
    db_url = public_url if public_url else raw_db_url
else:
    db_url = raw_db_url

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 2. Ticketmaster Scraper ---
def fetch_ticketmaster():
    events = []
    api_key = os.getenv("TM_API_KEY")
    if not api_key:
        print("Warning: TM_API_KEY not found in Environment Variables.")
        return events

    url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={api_key}&city=Atlanta&classificationName=music&size=20"
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
    except Exception as e:
        print(f"Ticketmaster error: {e}")
    return events

# --- 3. The Earl Scraper ---
def scrape_the_earl():
    events = []
    print("Scraping The Earl via Bandsintown...")
    with sync_playwright() as p:
        try:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')
            page = context.new_page()
            
            # The Earl's Bandsintown URL
            url = "https://www.bandsintown.com/v/10001781-the-earl"
            
            # Increase timeout and wait for the network to be quiet
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Look for the JSON data specifically
            # We'll try to find any script tag containing "Event"
            page.wait_for_selector('script[type="application/ld+json"]', timeout=10000)
            scripts = page.locator('script[type="application/ld+json"]').all()

            for script in scripts:
                content = script.evaluate("node => node.textContent").strip()
                if not content: continue
                
                try:
                    data = json.loads(content)
                except:
                    continue

                # Bandsintown often nests events in a @graph list
                items = data.get('@graph', [data]) if isinstance(data, dict) else data
                if not isinstance(items, list): items = [items]

                for item in items:
                    if isinstance(item, dict) and item.get('@type') == 'Event':
                        name = item.get('name', '')
                        start_str = item.get('startDate', '').split('T')[0]
                        
                        # Clean up the name (remove "at The Earl")
                        clean_name = re.sub(r'(\s*@\s*The\s*EARL.*|\s+at\s+The\s+EARL.*)', '', name, flags=re.I).strip()
                        
                        # Skip entries that are just the venue name
                        if clean_name.upper() == "THE EARL" or not clean_name: 
                            continue
                        
                        event_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                        events.append({
                            "tm_id": f"earl-{event_date}-{clean_name.lower()[:10]}",
                            "name": clean_name,
                            "date_time": event_date,
                            "venue_name": "The Earl",
                            "ticket_url": item.get('url', url)
                        })
            
            browser.close()
        except Exception as e:
            print(f"Earl Scraper error: {str(e)}")
    
    # Deduplicate in case the script found the same event twice in the JSON
    unique_events = {e['tm_id']: e for e in events}.values()
    return list(unique_events)

# --- 4. Sync to DB ---
def sync_to_db(combined_list):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    new_count = 0
    try:
        for event_data in combined_list:
            existing = db.query(Event).filter(Event.tm_id == event_data['tm_id']).first()
            if not existing:
                new_event = Event(**event_data)
                db.add(new_event)
                new_count += 1
        db.commit()
    finally:
        db.close()
    return new_count

if __name__ == "__main__":
    print("--- 1. Starting Collection ---")
    tm_shows = fetch_ticketmaster()
    print(f"Fetched {len(tm_shows)} Ticketmaster events.")
    
    earl_shows = scrape_the_earl()
    print(f"Scraped {len(earl_shows)} shows from The Earl.")
    
    total_added = sync_to_db(tm_shows + earl_shows)
    print(f"--- Finished. Added {total_added} new shows to Database. ---")