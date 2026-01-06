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
            
            # 1. Navigate
            page.goto("https://529atlanta.com/calendar/", wait_until="domcontentloaded", timeout=90000)
            
            # 2. WAIT for the dynamic content. 
            # We look for "High on Fire" specifically since we know they are playing.
            print("[*] Waiting for calendar content to render...")
            try:
                page.wait_for_selector("text=High on Fire", timeout=30000)
                print("[+] Found High on Fire on page!")
            except:
                print("[!] Timed out waiting for 'High on Fire' text. Scraping anyway...")

            # 3. Get Content
            content = page.locator("body").inner_text()
            
            # 4. Regex - Simplified to find High on Fire specifically
            # Matches: "Jan 23, 2026" ... "High on Fire"
            pattern = r"([a-zA-Z]{3}\s+\d{1,2},\s+202\d).*?High\s+on\s+Fire"
            
            for m in re.finditer(pattern, content, re.IGNORECASE):
                try:
                    date_str = m.group(1).strip()
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
        print("[!] No High on Fire dates found.")
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
    print(f"[+] Sync Complete. Added {new_count} High on Fire shows.")

if __name__ == "__main__":
    time.sleep(5)
    all_data = fetch_529()
    sync_to_db(all_data)