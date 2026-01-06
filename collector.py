import os
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine, Column, String, Date, Text
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
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

def scrape_529_direct():
    print("[*] Cracking 529 Atlanta Calendar...")
    shows = []
    
    with sync_playwright() as p:
        # 1. Launch Browser
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page()
        
        # 2. Go to the site and wait for the specific calendar classes to appear
        try:
            page.goto("https://529atlanta.com/calendar/", wait_until="domcontentloaded", timeout=60000)
            print("[*] Page loaded, waiting for JavaScript to build the calendar...")
            
            # This is the specific class 529's plugin uses for titles
            page.wait_for_selector(".simcal-event-title", timeout=30000)
            
            # 3. Pull the "Resolved" HTML (the stuff requests can't see)
            html_content = page.content()
            soup = BeautifulSoup(html_content, "lxml")
            
            # 4. Use your BeautifulSoup logic on the rendered HTML
            # 529's plugin puts dates in 'dt' tags and titles in '.simcal-event-title'
            calendar_items = soup.find_all("li", class_="simcal-event")
            
            for item in calendar_items:
                title_el = item.select_one(".simcal-event-title")
                # The date is usually hidden in a data attribute or a sibling span
                # We'll look for the most common placement
                details = item.get_text()
                
                if title_el and ("High on Fire" in title_el.text or "High On Fire" in title_el.text):
                    artist = title_el.text.strip()
                    
                    # We look for the date in the parent or surrounding text
                    # Regex to find "Jan 23, 2026" inside the event block
                    date_match = re.search(r"([a-zA-Z]{3}\s+\d{1,2},\s+202\d)", details)
                    
                    if date_match:
                        date_str = date_match.group(1)
                        clean_date = datetime.strptime(date_str, "%b %d, %Y").date()
                        
                        print(f"[!] Cracked it! Found {artist} on {clean_date}")
                        shows.append({
                            "tm_id": f"529-{clean_date}-hof",
                            "name": artist,
                            "date_time": clean_date,
                            "venue_name": "529",
                            "ticket_url": "https://529atlanta.com/calendar/"
                        })
        except Exception as e:
            print(f"[!] Error during crack: {e}")
        finally:
            browser.close()
            
    return shows

def sync_to_db(data):
    if not data:
        print("[!] No shows found. Selector might be off or site blocked the IP.")
        return
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    for item in data:
        if not db.query(Event).filter_by(tm_id=item['tm_id']).first():
            db.add(Event(**item))
    db.commit()
    db.close()
    print(f"[+] Synced {len(data)} items.")

if __name__ == "__main__":
    time.sleep(5)
    events = scrape_529_direct()
    sync_to_db(events)