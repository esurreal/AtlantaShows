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
    print("[*] Scraping 529...")
    events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            page = browser.new_page()
            # Navigate and wait for content
            page.goto("https://529atlanta.com/calendar/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            
            content = page.locator(".entry-content").inner_text()
            # Extremely flexible pattern to find High on Fire
            # Matches "Month Day, Year" ... "Artist"
            pattern = r"([a-zA-Z]{3}\s+\d{1,2},\s+202\d).*?[\-\–\—\.]\s*(.*?)(?=\n|Tickets|$)"
            
            for m in re.finditer(pattern, content):
                try:
                    date_str, artist = m.group(1), m.group(2).strip()
                    if "High on Fire" in artist or "High On Fire" in artist:
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
    except Exception as e: print(f"529 Error: {e}")
    return events

def sync_to_db(data):
    if not data: return
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    for item in data:
        if not db.query(Event).filter_by(tm_id=item['tm_id']).first():
            db.add(Event(**item))
    db.commit()
    db.close()
    print(f"Done. Synced {len(data)} items.")

if __name__ == "__main__":
    # Small delay to ensure DB is ready
    time.sleep(5)
    all_data = fetch_529()
    sync_to_db(all_data)