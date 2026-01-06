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
            
            # Use a longer timeout and wait for DOM rather than network idle
            page.goto("https://529atlanta.com/calendar/", wait_until="domcontentloaded", timeout=90000)
            
            # Wait for any of the common content containers to appear
            try:
                page.wait_for_selector("article, .entry-content, #main", timeout=20000)
            except:
                print("[!] Specific content container not found, trying body text...")

            # Pull the inner text from the whole body as a fallback
            content = page.locator("body").inner_text()
            
            # DEBUG: Print first 100 chars of found text to logs
            print(f"[Debug] Found text snippet: {content[:150].replace('\n', ' ')}")

            # Pattern for: "Friday Jan 23, 2026" or "Jan 23, 2026"
            # It looks for the date, then any character, then the band name
            pattern = r"([a-zA-Z]{3}\s+\d{1,2},\s+202\d).*?([\-\–\—\.\:\s])\s*(.*?)(?=\n|Tickets|Info|$)"
            
            for m in re.finditer(pattern, content, re.IGNORECASE):
                try:
                    date_str = m.group(1).strip()
                    artist_raw = m.group(3).strip()
                    
                    # Target High on Fire specifically
                    if "high on fire" in artist_raw.lower():
                        clean_date = datetime.strptime(date_str, "%b %d, %Y").date()
                        events.append({
                            "tm_id": f"529-{clean_date}-hof",
                            "name": "High On Fire",
                            "date_time": clean_date,
                            "venue_name": "529",
                            "ticket_url": "https://529atlanta.com/calendar/"
                        })
                except: continue
            browser.close()
    except Exception as e: 
        print(f"[!] 529 Error: {e}")
    return events

def sync_to_db(data):
    if not data: 
        print("[!] No events found to sync.")
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
    print(f"[+] Sync Complete. Added {new_count} new events.")

if __name__ == "__main__":
    # Wait for web server
    time.sleep(8)
    all_data = fetch_529()
    sync_to_db(all_data)