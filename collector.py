import os
import re
import json
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright
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
db_url = raw_db_url.replace("postgres://", "postgresql://", 1) if "postgres://" in raw_db_url else raw_db_url
engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 2. Ticketmaster Scraper ---
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
                "tm_id": str(item['id']),
                "name": item['name'],
                "date_time": datetime.strptime(item['dates']['start']['localDate'], '%Y-%m-%d').date(),
                "venue_name": item['_embedded']['venues'][0]['name'],
                "ticket_url": item['url']
            })
    except Exception as e: print(f"[!] TM Error: {e}")
    return events

# --- 3. Bandsintown Playwright Scraper (UPDATED) ---
def fetch_bandsintown_venue(venue_id, venue_display_name):
    venue_events = []
    print(f"[*] Scraping {venue_display_name}...")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/pw-browsers"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            page = context.new_page()
            
            page.goto(f"https://www.bandsintown.com/v/{venue_id}", wait_until="networkidle", timeout=60000)
            
            # FIX: Scroll down to trigger lazy-loading for shows later in the month (like High on Fire)
            for _ in range(3):
                page.mouse.wheel(0, 2000)
                time.sleep(1)

            scripts = page.locator('script[type="application/ld+json"]').all()
            for script in scripts:
                content = script.evaluate("node => node.textContent").strip()
                if not content: continue
                try:
                    data = json.loads(content)
                    items = data if isinstance(data, list) else data.get('@graph', [data])
                    for item in items:
                        if isinstance(item, dict) and 'startDate' in item:
                            raw_name = item.get('name', '')
                            date_str = item.get('startDate', '').split('T')[0]
                            
                            # FIX: Better Name Cleaning
                            # Instead of discarding if venue name is present, we just strip the venue name out
                            # This preserves "High on Fire @ 529" as "High on Fire"
                            clean_name = re.sub(rf'(@\s*{venue_display_name}|at\s*{venue_display_name}|{venue_display_name})', '', raw_name, flags=re.I).strip()
                            clean_name = re.sub(r'\s+', ' ', clean_name).strip() # clean extra spaces
                            
                            # Skip if name is empty or just punctuation after cleaning
                            if not clean_name or len(clean_name) < 2:
                                continue

                            venue_events.append({
                                "tm_id": f"bit-{venue_id}-{date_str}-{clean_name[:10].lower().replace(' ', '')}",
                                "name": clean_name,
                                "date_time": datetime.strptime(date_str, "%Y-%m-%d").date(),
                                "venue_name": venue_display_name,
                                "ticket_url": item.get('url', '').split('?')[0]
                            })
                except: continue
            browser.close()
    except Exception as e: print(f"[!] {venue_display_name} Error: {e}")
    return venue_events

# --- 4. Sync ---
def sync_to_db(combined_list):
    if not combined_list: return 0
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    new_count = 0
    try:
        for event_data in combined_list:
            existing = db.query(Event).filter(
                and_(Event.date_time == event_data['date_time'], 
                     Event.venue_name == event_data['venue_name'],
                     Event.name == event_data['name'])
            ).first()
            if not existing:
                db.add(Event(**event_data))
                new_count += 1
        db.commit()
    except Exception as e:
        print(f"[!] DB Error: {e}")
        db.rollback()
    finally: db.close()
    return new_count

if __name__ == "__main__":
    all_shows = fetch_ticketmaster()
    small_venues = [
        {"id": "10001781", "name": "The Earl"},
        {"id": "10243412", "name": "Boggs Social"},
        {"id": "10005523", "name": "529"},
        {"id": "10001815", "name": "The Drunken Unicorn"}
    ]
    for v in small_venues:
        all_shows.extend(fetch_bandsintown_venue(v['id'], v['name']))
    
    added = sync_to_db(all_shows)
    print(f"Done. Added {added} new shows.")