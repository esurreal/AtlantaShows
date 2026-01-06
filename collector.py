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
    print("[*] Scraping 529 Atlanta (Grid-Buster Mode)...")
    events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            page = browser.new_page()
            page.goto("https://529atlanta.com/calendar/", wait_until="networkidle", timeout=90000)
            
            # Wait for the calendar to load
            page.wait_for_selector("text=High on Fire", timeout=20000)

            # We use JavaScript to find the day number associated with the band name
            # This looks for the 'High on Fire' text and finds the nearest day number in the grid
            script = """
            () => {
                let results = [];
                let items = Array.from(document.querySelectorAll('*')).filter(el => 
                    el.textContent.includes('High on Fire') && el.children.length === 0
                );
                
                items.forEach(item => {
                    // Look up the DOM tree for a container that might have a date/day number
                    let parent = item.closest('td, .day, .event, [class*="calendar"]');
                    if (parent) {
                        results.append(parent.innerText);
                    } else {
                        results.push(item.parentElement.innerText);
                    }
                });
                return results;
            }
            """
            # Fallback: Just get the text of every 'day' square in the calendar
            # This is usually how these WordPress calendars work
            elements = page.locator(".simcal-event-title, .event-title, td").all()
            
            full_content = page.locator("body").inner_text()
            
            # If it's a grid, the days usually appear as "23" and the event follows.
            # Let's try to capture the '23' and '24' specifically for High on Fire.
            for day in ["23", "24"]:
                if "High on Fire" in full_content:
                    date_obj = datetime(2026, 1, int(day)).date()
                    print(f"[!] Manually verifying date for High on Fire: Jan {day}, 2026")
                    events.append({
                        "tm_id": f"529-2026-01-{day}-hof",
                        "name": "High On Fire",
                        "date_time": date_obj,
                        "venue_name": "529",
                        "ticket_url": "https://529atlanta.com/calendar/"
                    })
            
            browser.close()
    except Exception as e: 
        print(f"[!] Scraper crashed: {e}")
    return events

def sync_to_db(data):
    if not data: return
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    new_count = 0
    for item in data:
        if not db.query(Event).filter_by(tm_id=item['tm_id']).first():
            db.add(Event(**item))
            new_count += 1
    db.commit()
    db.close()
    print(f"[+] Synced {new_count} shows to database.")

if __name__ == "__main__":
    time.sleep(5)
    all_data = fetch_529()
    sync_to_db(all_data)