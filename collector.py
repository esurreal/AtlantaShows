import os
import re
import json
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright
# The new way to import stealth in version 2.0.0+
from playwright_stealth import Stealth
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

# --- 2. 529 Direct Website Scraper ---
def fetch_529_direct():
    print("[*] Scraping 529 Atlanta Official Calendar...")
    events = []
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/pw-browsers"
    
    try:
        with sync_playwright() as p:
            # Use Stealth() as a context manager for the latest API
            with Stealth().use_sync(p) as stealth_p:
                browser = stealth_p.chromium.launch(headless=True, args=['--no-sandbox'])
                page = browser.new_page()
                
                # Go to the 529 calendar
                page.goto("https://529atlanta.com/calendar/", wait_until="networkidle", timeout=60000)
                time.sleep(2)
                
                content = page.locator(".entry-content").inner_text()
                
                # Looking for: Day Jan 23, 2026. Artist
                pattern = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+([a-zA-Z]{3}\s+\d{1,2},\s+202\d)\.\s+(.*?)(?=\s+Tickets|\s+Info|\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)|$)"
                
                matches = re.finditer(pattern, content, re.DOTALL)
                for m in matches:
                    try:
                        date_str = m.group(1).strip() # "Jan 23, 2026"
                        artist_raw = m.group(2).strip()
                        clean_date = datetime.strptime(date_str, "%b %d, %Y").date()
                        artist = re.sub(r'^(Night \d\.\s+|w\/\s+)', '', artist_raw, flags=re.I).strip()
                        
                        if artist and len(artist) > 2:
                            events.append({
                                "tm_id": f"529-{clean_date}-{artist[:10].lower().replace(' ', '')}",
                                "name": artist,
                                "date_time": clean_date,
                                "venue_name": "529",
                                "ticket_url": "https://529atlanta.com/calendar/"
                            })
                    except: continue
                browser.close()
    except Exception as e: print(f"[!] 529 Error: {e}")
    return events

# --- 3. Bandsintown Scraper (The Earl, Boggs, etc.) ---
def fetch_bandsintown_venue(venue_id, venue_display_name):
    venue_events = []
    print(f"[*] Scraping {venue_display_name} via BIT...")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/pw-browsers"

    try:
        with sync_playwright() as p:
            with Stealth().use_sync(p) as stealth_p:
                browser = stealth_p.chromium.launch(headless=True, args=['--no-sandbox'])
                page = browser.new_page()
                page.goto(f"https://www.bandsintown.com/v/{venue_id}", wait_until="networkidle", timeout=60000)
                
                # Scroll to load the full month
                for _ in range(3):
                    page.mouse.wheel(0, 1000)
                    time.sleep(1)

                scripts = page.locator('script[type="application/ld+json"]').all()
                for script in scripts:
                    try:
                        data = json.loads(script.evaluate("node => node.textContent"))
                        items = data if isinstance(data, list) else data.get('@graph', [data])
                        for item in items:
                            if isinstance(item, dict) and 'startDate' in item:
                                raw_name = item.get('name', '')
                                clean_name = re.sub(rf'(@\s*{venue_display_name}|at\s*{venue_display_name}|{venue_display_name})', '', raw_name, flags=re.I).strip()
                                date_str = item.get('startDate', '').split('T')[0]
                                
                                venue_events.append({
                                    "tm_id": f"bit-{venue_id}-{date_str}-{clean_name[:5].lower()}",
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
            # Check if this show on this date already exists
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
    print("--- Collection Started ---")
    all_shows = []
    
    # 529 Direct
    all_shows.extend(fetch_529_direct())
    
    # Other Indie Venues
    venues = [
        {"id": "10001781", "name": "The Earl"},
        {"id": "10427847", "name": "Boggs Social"},
        {"id": "10001815", "name": "The Drunken Unicorn"}
    ]
    for v in venues:
        all_shows.extend(fetch_bandsintown_venue(v['id'], v['name']))
        time.sleep(2)

    added = sync_to_db(all_shows)
    print(f"--- Finished. Added {added} new shows. ---")