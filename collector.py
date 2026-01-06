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
    print("[*] Scraping 529 Atlanta...")
    events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page = context.new_page()
            
            page.goto("https://529atlanta.com/calendar/", wait_until="domcontentloaded", timeout=90000)
            
            print("[*] Waiting for calendar content to render...")
            try:
                # Wait for the specific text to be visible
                page.wait_for_selector("text=High on Fire", timeout=30000)
                print("[+] Found High on Fire on page!")
            except:
                print("[!] Could not find 'High on Fire' text via selector.")

            # Get the text of the entire page content
            content = page.content() 
            # We use page.content() to get raw HTML text as well, 
            # but let's stick to inner_text for cleaner matching first.
            text_content = page.locator("body").inner_text()
            
            # --- THE NUCLEAR REGEX ---
            # 1. Finds a date: "Jan 23, 2026"
            # 2. Uses (?s) to allow . to match newlines
            # 3. Uses {0,500} to look ahead up to 500 characters for the band name
            pattern = r"(?i)([a-z]{3}\s+\d{1,2},\s+202\d)(?s:.*?)(High\s+on\s+Fire)"
            
            for m in re.finditer(pattern, text_content):
                try:
                    date_str = m.group(1).strip()
                    # Convert "Jan 23, 2026" to date object
                    clean_date = datetime.strptime(date_str, "%b %d, %Y").date()
                    
                    print(f"[!] Match found: {date_str} -> High on Fire")
                    
                    events.append({
                        "tm_id": f"529-{clean_date}-hof",
                        "name": "High On Fire",
                        "date_time": clean_date,
                        "venue_name": "529",
                        "ticket_url": "https://529atlanta.com/calendar/"
                    })
                except Exception as e:
                    print(f"[!] Regex processing error: {e}")
            
            browser.close()
    except Exception as e: 
        print(f"[!] Scraper crashed: {e}")
    return events

def sync_to_db(data):
    if not data: 
        print("[!] No High on Fire dates captured in the list.")
        return
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    new_count = 0
    for item in data:
        existing = db.query(Event).filter_by(tm_id=item['tm_id']).first()
        if not existing:
            db.add(Event(**item))
            new_count += 1
    db.commit()
    db.close()
    print(f"[+] SUCCESS! Added {new_count} High on Fire shows to the database.")

if __name__ == "__main__":
    time.sleep(5)
    all_data = fetch_529()
    sync_to_db(all_data)