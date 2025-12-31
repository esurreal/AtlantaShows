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

# DATABASE LOGIC
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
    if not api_key:
        print("Warning: TM_API_KEY not found.")
        return events

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
    except Exception as e:
        print(f"Ticketmaster error: {e}")
    return events

# --- 3. The Earl Scraper (Fast-Load Mode) ---
def scrape_the_earl():
    found_events = []
    print("Scraping The Earl via Bandsintown...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            url = "https://www.bandsintown.com/v/10001781-the-earl"
            
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(7000) 
            
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
                            if not raw_name or raw_name.upper() == "THE EARL":
                                continue
                                
                            clean_name = re.sub(r'(\s*@\s*The\s*EARL.*|\s+at\s+The\s+EARL.*)', '', raw_name, flags=re.I).strip()
                            start_str = item.get('startDate', '').split('T')[0]
                            
                            try:
                                event_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                                event_id = f"earl-{event_date}-{clean_name.lower()[:8]}".replace(" ", "")
                                
                                found_events.append({
                                    "tm_id": event_id,
                                    "name": clean_name,
                                    "date_time": event_date,
                                    "venue_name": "The Earl",
                                    "ticket_url": item.get('url', url)
                                })
                            except: continue
                except: continue
            
            browser.close()
        except Exception as e:
            print(f"Earl Scraper error: {str(e)}")
    
    unique_dict = {e['tm_id']: e for e in found_events}
    return list(unique_dict.values())

# --- 4. Sync to DB ---
def sync_to_db(combined_list):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    new_count = 0
    try:
        for event_data in combined_list:
            # FIXED: Corrected the and_() syntax to avoid the ArgumentError
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
    except Exception as e:
        print(f"Sync Error: {e}")
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