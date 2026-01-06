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

# --- 2. 529 Direct Scraper (Sunday Calendar Specialist) ---
def fetch_529_direct():
    print("[*] Scraping 529 Atlanta...")
    events = []
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/pw-browsers"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page = context.new_page()
            
            # Navigate to the calendar
            page.goto("https://529atlanta.com/calendar/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(6) # Extra time for the calendar grid to populate
            
            # 529 often uses a 'list' view or a table. We'll grab all text in the main content area.
            content = page.locator(".entry-content").inner_text()
            
            # Print a snippet to logs so we can debug if it fails again
            print(f"[Debug] 529 Text Snippet: {content[:200].replace('\n', ' ')}")

            # Pattern optimized for: "Friday, Jan 23, 2026 - High On Fire" 
            # or "Jan 23, 2026. High On Fire"
            pattern = r"([a-zA-Z]{3}\s+\d{1,2},\s+202\d).*?[\-\.\–\—]\s*(.*?)(?=\n|Tickets|Info|$)"
            
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for m in matches:
                try:
                    date_str = m.group(1).strip()
                    artist_raw = m.group(2).strip()
                    
                    # Clean up the artist name
                    artist = re.sub(r'^(Night \d\.\s+|529 Presents:\s+|w\/\s+)', '', artist_raw, flags=re.I).strip()
                    artist = artist.split('\n')[0].strip()
                    
                    # Convert "Jan 23, 2026" to date object
                    clean_date = datetime.strptime(date_str, "%b %d, %Y").date()
                    
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
            print(f"[+] 529: Found {len(events)} shows.")
    except Exception as e: print(f"[!] 529 Error: {e}")
    return events

# --- 3. Boggs Scraper ---
def fetch_boggs_direct():
    print("[*] Scraping Boggs Social...")
    events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            page = browser.new_page()
            page.goto("https://www.boggssocial.com/events", wait_until="domcontentloaded", timeout=60000)
            time.sleep(4)
            
            articles = page.locator("article.eventlist-event").all()
            for art in articles:
                try:
                    title = art.locator("h1.eventlist-title").inner_text()
                    date_val = art.locator("time.eventlist-meta-time").get_attribute("datetime")
                    events.append({
                        "tm_id": f"boggs-{date_val}-{title[:5].lower().replace(' ', '')}",
                        "name": title.strip(),
                        "date_time": datetime.strptime(date_val, "%Y-%m-%d").date(),
                        "venue_name": "Boggs Social",
                        "ticket_url": "https://www.boggssocial.com/events"
                    })
                except: continue
            browser.close()
            print(f"[+] Boggs: Found {len(events)} shows.")
    except Exception as e: print(f"[!] Boggs Error: {e}")
    return events

# --- 4. The Earl ---
def fetch_earl_bit():
    print("[*] Scraping The Earl...")
    events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            page = browser.new_page()
            page.goto("https://www.bandsintown.com/v/10001781", wait_until="domcontentloaded")
            time.sleep(3)
            scripts = page.locator('script[type="application/ld+json"]').all()
            for script in scripts:
                try:
                    data = json.loads(script.evaluate("node => node.textContent"))
                    items = data if isinstance(data, list) else data.get('@graph', [data])
                    for item in items:
                        if isinstance(item, dict) and 'startDate' in item:
                            name = item.get('name', '').split('@')[0].split('at')[0].strip()
                            date_str = item.get('startDate', '').split('T')[0]
                            events.append({
                                "tm_id": f"bit-earl-{date_str}-{name[:5].lower()}",
                                "name": name,
                                "date_time": datetime.strptime(date_str, "%Y-%m-%d").date(),
                                "venue_name": "The Earl",
                                "ticket_url": item.get('url', '').split('?')[0]
                            })
                except: continue
            browser.close()
    except: pass
    return events

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
    except Exception as e: print(f"[!] DB Error: {e}")
    finally: db.close()
    return new_count

if __name__ == "__main__":
    # Wait for web server to avoid 502
    time.sleep(10)
    all_shows = []
    all_shows.extend(fetch_529_direct())
    all_shows.extend(fetch_boggs_direct())
    all_shows.extend(fetch_earl_bit())
    added = sync_to_db(all_shows)
    print(f"--- Finished. Added {added} new shows. ---")