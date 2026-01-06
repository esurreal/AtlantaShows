import os
import re
import json
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from sqlalchemy import create_engine, Column, String, Date, Text, and_
from sqlalchemy.orm import declarative_base, sessionmaker

# --- Database Setup ---
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

def fetch_529_direct():
    print("[*] Scraping 529 Atlanta (Stealth Mode)...")
    events = []
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/pw-browsers"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 800}
            )
            page = context.new_page()
            # Apply Stealth
            stealth_sync(page)
            
            page.goto("https://529atlanta.com/calendar/", wait_until="networkidle", timeout=60000)
            time.sleep(3) # Let the scripts settle
            
            content = page.locator(".entry-content").inner_text()
            
            # Pattern for: Friday Jan 23, 2026. ARTIST NAME
            pattern = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+([a-zA-Z]{3}\s+\d{1,2},\s+202\d)\.\s+(.*?)(?=\s+Tickets|\s+Info|\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)|$)"
            
            matches = re.finditer(pattern, content, re.DOTALL)
            for m in matches:
                try:
                    date_str = m.group(1).strip()
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
            print(f"[+] 529: Found {len(events)} events.")
    except Exception as e: print(f"[!] 529 Error: {e}")
    return events

def fetch_bandsintown_venue(venue_id, venue_display_name):
    venue_events = []
    print(f"[*] Scraping {venue_display_name} via BIT (Stealth Mode)...")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/pw-browsers"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            stealth_sync(page)
            
            page.goto(f"https://www.bandsintown.com/v/{venue_id}", wait_until="networkidle", timeout=60000)
            
            # Mimic a human scrolling down slowly
            for _ in range(3):
                page.mouse.wheel(0, 800)
                time.sleep(1.5)

            scripts = page.locator('script[type="application/ld+json"]').all()
            for script in scripts:
                try:
                    data = json.loads(script.evaluate("node => node.textContent"))
                    items = data if isinstance(data, list) else data.get('@graph', [data])
                    for item in items:
                        if isinstance(item, dict) and 'startDate' in item:
                            name = item.get('name', '')
                            name = re.sub(rf'(@\s*{venue_display_name}|at\s*{venue_display_name}|{venue_display_name})', '', name, flags=re.I).strip()
                            date_str = item.get('startDate', '').split('T')[0]
                            
                            venue_events.append({
                                "tm_id": f"bit-{venue_id}-{date_str}-{name[:5].lower()}",
                                "name": name,
                                "date_time": datetime.strptime(date_str, "%Y-%m-%d").date(),
                                "venue_name": venue_display_name,
                                "ticket_url": item.get('url', '').split('?')[0]
                            })
                except: continue
            browser.close()
    except Exception as e: print(f"[!] {venue_display_name} Error: {e}")
    return venue_events

def sync_to_db(combined_list):
    if not combined_list: return 0
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    new_count = 0
    try:
        for event_data in combined_list:
            existing = db.query(Event).filter(
                and_(Event.date_time == event_data['date_time'], 
                     Event.venue_name == event_data['venue_name'])
            ).first()
            if not existing:
                db.add(Event(**event_data))
                new_count += 1
        db.commit()
    except: db.rollback()
    finally: db.close()
    return new_count

if __name__ == "__main__":
    print("--- Collection Started ---")
    all_shows = []
    
    # 1. Ticketmaster (API - No stealth needed)
    tm_api_key = os.getenv("TM_API_KEY")
    if tm_api_key:
        url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={tm_api_key}&city=Atlanta&classificationName=music&size=100&sort=date,asc"
        try:
            r = requests.get(url, timeout=10)
            for item in r.json().get('_embedded', {}).get('events', []):
                all_shows.append({
                    "tm_id": str(item['id']),
                    "name": item['name'],
                    "date_time": datetime.strptime(item['dates']['start']['localDate'], '%Y-%m-%d').date(),
                    "venue_name": item['_embedded']['venues'][0]['name'],
                    "ticket_url": item['url']
                })
        except: print("[!] Ticketmaster API failed.")

    # 2. 529 Direct
    all_shows.extend(fetch_529_direct())
    
    # 3. Others via BIT
    venues = [
        {"id": "10001781", "name": "The Earl"},
        {"id": "10427847", "name": "Boggs Social"},
        {"id": "10001815", "name": "The Drunken Unicorn"}
    ]
    for v in venues:
        all_shows.extend(fetch_bandsintown_venue(v['id'], v['name']))
        time.sleep(5) # Be very respectful with timing

    added = sync_to_db(all_shows)
    print(f"--- Finished. Added {added} new shows. ---")