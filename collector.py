import os
import re
import json
import requests
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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

# DATABASE LOGIC: Handle Internal vs Public Railway URLs
raw_db_url = os.getenv("DATABASE_URL", "sqlite:///shows.db")

# If running locally, railway run might give us the .internal address.
# We must use the Public URL to connect from your home computer.
if "postgres.railway.internal" in raw_db_url:
    public_url = os.getenv("DATABASE_PUBLIC_URL")
    if public_url:
        db_url = public_url
    else:
        db_url = raw_db_url
else:
    db_url = raw_db_url

# Fix for older SQLAlchemy versions requiring 'postgresql://' instead of 'postgres://'
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 2. Ticketmaster Scraper ---
def fetch_ticketmaster():
    events = []
    api_key = os.getenv("TM_API_KEY")
    if not api_key:
        print("Warning: TM_API_KEY not found.")
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

# --- 3. The Earl (Bandsintown) Scraper ---
def scrape_the_earl():
    events = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        url = "https://www.bandsintown.com/v/10001781-the-earl"
        
        try:
            page.goto(url, wait_until="commit", timeout=60000)
            page.wait_for_selector('script[type="application/ld+json"]', state="attached", timeout=15000)
            scripts = page.locator('script[type="application/ld+json"]').all()

            for script in scripts:
                content = script.evaluate("node => node.textContent").strip()
                if not content: continue
                data = json.loads(content)
                items = data.get('@graph', [data]) if isinstance(data, dict) else data

                for item in items:
                    if isinstance(item, dict) and 'startDate' in item:
                        name = item.get('name', '')
                        start_str = item.get('startDate', '').split('T')[0]
                        clean_name = re.sub(r'(\s*@\s*The\s*EARL.*|\s+at\s+The\s+EARL.*)', '', name, flags=re.I).strip()
                        
                        if clean_name.upper() == "THE EARL": continue
                        
                        event_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                        events.append({
                            "tm_id": f"earl-{event_date}-{clean_name.lower()[:10]}",
                            "name": clean_name,
                            "date_time": event_date,
                            "venue_name": "The Earl",
                            "ticket_url": item.get('url', url)
                        })
        except Exception as e:
            print(f"Earl Scraper error: {e}")
        finally:
            browser.close()
    return events

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

# --- 5. Main Execution ---
if __name__ == "__main__":
    print("--- 1. Starting Collection ---")
    tm_shows = fetch_ticketmaster()
    print(f"Fetched {len(tm_shows)} Ticketmaster events.")
    
    earl_shows = scrape_the_earl()
    print(f"Scraped {len(earl_shows)} shows from The Earl.")
    
    total_added = sync_to_db(tm_shows + earl_shows)
    print(f"--- Finished. Added {total_added} new shows to Database. ---")