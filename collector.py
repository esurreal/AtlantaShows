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

# --- 3. 529 Scraper ---
def scrape_529(page):
    found_events = []
    print("Scraping 529...")
    url = "https://529atlanta.com/"
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        # Look for the show items on the home page/calendar
        show_elements = page.locator(".show-info").all() # Based on common 529 structure
        
        for show in show_elements:
            try:
                name = show.locator("h2, h3").first.inner_text().strip()
                date_str = show.locator(".show-date").first.inner_text().strip()
                # 529 dates often look like "Saturday Jan 03, 2026"
                # We extract the part that looks like a date
                clean_date_str = re.search(r'[A-Za-z]+\s+\d{1,2},\s+\d{4}', date_str).group(0)
                event_date = datetime.strptime(clean_date_str, "%b %d, %Y").date()
                
                link_el = show.locator("a").first
                link = link_el.get_attribute("href") if link_el else url
                
                found_events.append({
                    "tm_id": f"529-{event_date}-{name.lower()[:5]}".replace(" ", ""),
                    "name": name,
                    "date_time": event_date,
                    "venue_name": "529",
                    "ticket_url": link if link.startswith("http") else f"https://529atlanta.com{link}"
                })
            except: continue
    except Exception as e:
        print(f"529 specific error: {e}")
    return found_events

# --- 4. The Drunken Unicorn (BigTickets Scraper) ---
def scrape_drunken_unicorn(page):
    found_events = []
    print("Scraping Drunken Unicorn...")
    url = "https://www.thedrunkenunicornatl.com/events"
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_selector(".eventlist-title", timeout=10000)
        titles = page.locator(".eventlist-title").all()
        dates = page.locator("time.eventlist-datetimestart").all()
        links = page.locator(".eventlist-readmore-link").all()

        for i in range(len(titles)):
            name = titles[i].inner_text().strip()
            raw_date = dates[i].get_attribute("datetime")
            event_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
            event_url = links[i].get_attribute("href")
            
            found_events.append({
                "tm_id": f"du-{event_date}-{name.lower()[:5]}".replace(" ", ""),
                "name": name,
                "date_time": event_date,
                "venue_name": "The Drunken Unicorn",
                "ticket_url": f"https://www.thedrunkenunicornatl.com{event_url}" if event_url.startswith("/") else event_url
            })
    except Exception as e:
        print(f"Drunken Unicorn specific error: {e}")
    return found_events

# --- 5. Modular Bandsintown Scraper ---
def scrape_bandsintown_venue(page, venue_id, venue_display_name):
    found_events = []
    url = f"https://www.bandsintown.com/v/{venue_id}"
    print(f"Scraping {venue_display_name}...")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000) 
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
                elif isinstance(data, list): to_check.extend(data)

                for item in to_check:
                    if isinstance(item, dict) and 'name' in item and 'startDate' in item:
                        raw_name = item.get('name', '')
                        if not raw_name or raw_name.upper() in [venue_display_name.upper(), "BANDSINTOWN"]:
                            continue
                        clean_name = re.sub(r'(\s*@\s*.*|\s+at\s+.*)', '', raw_name, flags=re.I).strip()
                        start_str = item.get('startDate', '').split('T')[0]
                        event_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                        found_events.append({
                            "tm_id": f"{venue_display_name[:2].lower()}-{event_date}-{clean_name.lower()[:5]}".replace(" ", ""),
                            "name": clean_name,
                            "date_time": event_date,
                            "venue_name": venue_display_name,
                            "ticket_url": item.get('url', url)
                        })
            except: continue
    except Exception as e:
        print(f"Error scraping {venue_display_name}: {e}")
    return found_events

# --- 6. Sync to DB ---
def sync_to_db(combined_list):
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
        today = datetime.now().date()
        db.query(Event).filter(Event.date_time < today).delete()
        db.commit()
    finally:
        db.close()
    return new_count

if __name__ == "__main__":
    all_shows = fetch_ticketmaster()
    
    # Venues using the Bandsintown method
    bit_venues = [
        {"id": "10001781", "name": "The Earl"},
        {"id": "10243412", "name": "Boggs Social"},
        {"id": "10007886", "name": "Eyedrum"},
        {"id": "11466023", "name": "Culture Shock"}
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        page = context.new_page()
        
        # 1. Scrape Bandsintown venues
        for v in bit_venues:
            all_shows.extend(scrape_bandsintown_venue(page, v['id'], v['name']))
        
        # 2. Scrape 529
        all_shows.extend(scrape_529(page))
        
        # 3. Scrape Drunken Unicorn
        all_shows.extend(scrape_drunken_unicorn(page))
        
        browser.close()

    total = sync_to_db(all_shows)
    print(f"--- Finished. Total new shows added: {total} ---")