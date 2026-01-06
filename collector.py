import os
import re
import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine, Column, String, Date, Text, and_
from sqlalchemy.orm import declarative_base, sessionmaker

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

def fetch_529():
    print("[*] Scraping 529 Atlanta via Proximity Search...")
    events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            page = browser.new_page()
            page.goto("https://529atlanta.com/calendar/", wait_until="domcontentloaded", timeout=90000)
            
            # Wait for the band name to appear
            try:
                hof_elements = page.get_by_text("High on Fire", exact=False)
                page.wait_for_selector("text=High on Fire", timeout=20000)
                
                count = hof_elements.count()
                print(f"[+] Found {count} instances of High on Fire.")

                for i in range(count):
                    # For each "High on Fire" mention, look at the surrounding text block
                    # Squarespace and WordPress often put the date in a 'time' tag 
                    # or a sibling div. We'll grab the parent container's text.
                    container_text = hof_elements.nth(i).locator("xpath=..").inner_text()
                    
                    # Also try the parent's parent just in case
                    wide_text = hof_elements.nth(i).locator("xpath=../..").inner_text()
                    
                    combined = container_text + " " + wide_text
                    
                    # Search for the date in this specific small block of text
                    date_match = re.search(r"([a-zA-Z]{3}\s+\d{1,2},\s+202\d)", combined)
                    
                    if date_match:
                        date_str = date_match.group(1).strip()
                        clean_date = datetime.strptime(date_str, "%b %d, %Y").date()
                        print(f"[!] Success! Found date {clean_date} for High on Fire")
                        
                        events.append({
                            "tm_id": f"529-{clean_date}-hof",
                            "name": "High On Fire",
                            "date_time": clean_date,
                            "venue_name": "529",
                            "ticket_url": "https://529atlanta.com/calendar/"
                        })
            except Exception as e:
                print(f"[!] Proximity search failed: {e}")
            
            browser.close()
    except Exception as e: 
        print(f"[!] Scraper crashed: {e}")
    return events

def sync_to_db(data):
    if not data: 
        print("[!] Still no dates captured. Venue site layout is non-standard.")
        return
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    new_count = 0
    for item in data:
        # Use a more robust check for existing items
        existing = db.query(Event).filter(
            and_(Event.date_time == item['date_time'], Event.name == item['name'])
        ).first()
        if not existing:
            db.add(Event(**item))
            new_count += 1
    db.commit()
    db.close()
    print(f"[+] SUCCESS! Added {new_count} High on Fire shows.")

if __name__ == "__main__":
    time.sleep(5)
    all_data = fetch_529()
    sync_to_db(all_data)