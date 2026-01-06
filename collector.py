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

# --- 2. 529 Direct Website Scraper ---
def fetch_529_direct():
    print("[*] Scraping 529 Atlanta Official Calendar...")
    events = []
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/pw-browsers"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            # We set a real User-Agent manually to avoid being blocked
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.goto("https://529atlanta.com/calendar/", wait_until="networkidle", timeout=60000)
            
            content = page.locator(".entry-content").inner_text()
            
            # Pattern: Day Jan 23, 2026. Artist
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
    except Exception as e: print(f"[!] 529 Error: {e}")
    return events

# --- 3. Boggs Social Direct Scraper ---
def fetch_boggs_direct():
    print("[*] Scraping Boggs Social Official Website...")
    events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page = context.new_page()
            page.goto("https://www.boggssocial.com/events", wait_until="networkidle", timeout=60000)
            
            # Targeted selector for Squarespace events
            elements = page.locator("article.eventlist-event").all()
            for el in elements:
                try:
                    title = el.locator(".eventlist-title").inner_text()
                    date_raw = el.locator("time.eventlist-meta-time").get_attribute("datetime")
                    
                    clean_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
                    events.append({
                        "tm_id": f"boggs-{clean_date}-{title[:10].lower().replace(' ', '')}",
                        "name": title.strip(),
                        "date_time": clean_date,
                        "venue_name": "Boggs Social",
                        "ticket_url": "https://www.boggssocial.com/events"
                    })
                except: continue
            browser.close()
    except Exception as e: print(f"[!] Boggs Error: {e}")
    return events

# --- 4. Bandsintown (For The Earl & others) ---
def fetch_bandsintown_venue(venue_id, venue_display_name):
    venue_events = []
    print(f"[*] Scraping {venue_display_name} via BIT...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
            page = context.new_page()
            page.goto(f"https://www.bandsintown.com/v/{venue_id}", wait_until="domcontentloaded", timeout=60000)
            
            # Simple scroll
            page.mouse.wheel(0, 1500)
            time.sleep(2)

            scripts = page.locator('script[type="application/ld+json"]').all()
            for script in scripts:
                try:
                    data = json.loads(script.evaluate("node => node.textContent"))
                    items = data if isinstance(data, list) else data.get('@graph', [data])
                    for item in items:
                        if isinstance(item, dict) and 'startDate' in item:
                            name = item.get('name', '').split('@')[0].strip()
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
    except: pass
    return venue_events

# --- 5. Sync ---
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
    except: db.rollback()
    finally: db.close()
    return new_count

if __name__ == "__main__":
    print("--- Collection Started ---")
    all_shows = []
    
    # 1. Ticketmaster API
    tm_api_key = os.getenv("TM_API_KEY")
    if tm_api_key:
        try:
            url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={tm_api_key}&city=Atlanta&classificationName=music&size=100"
            r = requests.get(url, timeout=10)
            for item in r.json().get('_embedded', {}).get('events', []):
                all_shows.append({
                    "tm_id": str(item['id']),
                    "name": item['name'],
                    "date_time": datetime.strptime(item['dates']['start']['localDate'], '%Y-%m-%d').date(),
                    "venue_name": item['_embedded']['venues'][0]['name'],
                    "ticket_url": item['url']
                })
        except: print("[!] TM API failed.")

    # 2. Direct Scrapers
    all_shows.extend(fetch_529_direct())
    all_shows.extend(fetch_boggs_direct())
    
    # 3. BIT Scrapers
    all_shows.extend(fetch_bandsintown_venue("10001781", "The Earl"))
    all_shows.extend(fetch_bandsintown_venue("10001815", "The Drunken Unicorn"))

    added = sync_to_db(all_shows)
    print(f"--- Finished. Added {added} new shows. ---")