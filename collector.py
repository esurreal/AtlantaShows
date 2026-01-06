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
    print("[*] Scraping 529 Atlanta (Deep Scan Mode)...")
    events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            page = browser.new_page()
            page.goto("https://529atlanta.com/calendar/", wait_until="domcontentloaded", timeout=90000)
            
            # Wait for the content to actually exist
            page.wait_for_selector("text=High on Fire", timeout=20000)
            
            # Extract all text and normalize it (remove tabs and double spaces)
            raw_text = page.locator("body").inner_text()
            clean_text = " ".join(raw_text.split())
            
            print(f"[Debug] Normalized Snippet: {clean_text[:200]}")

            # This regex looks for: 
            # 1. A month (Jan/January)
            # 2. A day (23)
            # 3. A year (2026)
            # 4. Up to 100 characters of anything
            # 5. "High on Fire"
            pattern = r"([a-zA-Z]{3,9}\s+\d{1,2},\s+202\d).*?(High\s+on\s+Fire)"
            
            matches = re.finditer(pattern, clean_text, re.IGNORECASE)
            
            for m in matches:
                try:
                    date_str = m.group(1).strip()
                    # Use a flexible date parser for "Jan 23, 2026" or "January 23, 2026"
                    try:
                        clean_date = datetime.strptime(date_str, "%b %d, %Y").date()
                    except:
                        clean_date = datetime.strptime(date_str, "%B %d, %Y").date()
                        
                    print(f"[!] SUCCESS: Found {clean_date}")
                    events.append({
                        "tm_id": f"529-{clean_date}-hof",
                        "name": "High On Fire",
                        "date_time": clean_date,
                        "venue_name": "529",
                        "ticket_url": "https://529atlanta.com/calendar/"
                    })
                except Exception as e:
                    print(f"[!] Date Parse Error: {e}")
            
            browser.close()
    except Exception as e: 
        print(f"[!] Scraper crashed: {e}")
    return events

def sync_to_db(data):
    if not data: 
        print("[!] No High on Fire shows matched the date pattern.")
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
    print(f"[+] Synced {new_count} shows to database.")

if __name__ == "__main__":
    time.sleep(5)
    all_data = fetch_529()
    sync_to_db(all_data)