import os
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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

# Keep manual data for venues that don't use Freshtix (like 529)
VERIFIED_529_DATA = [
    {"date": "2026-01-23", "name": "High On Fire (w/ Hot Ram, Cheap Cigar)"},
    {"date": "2026-01-24", "name": "High On Fire (w/ Apostle, Big Oaf)"},
    {"date": "2026-01-29", "name": "Graveyard Hours (w/ Triangle Fire, Rosa Asphyxia)"},
    {"date": "2026-01-30", "name": "Joshua Quimby (Solo)"},
    {"date": "2026-01-31", "name": "Too Hot For Leather (Yevara, Vices of Vanity)"}
]

def scrape_freshtix():
    print("[*] Scraping Freshtix for Atlanta events...")
    events = []
    # Scraping the first 3 pages to capture Jan/Feb/March
    for page in range(1, 4):
        url = f"https://www.freshtix.com/events/state/GA/city/Atlanta?events_page={page}"
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Freshtix lists events in table rows or specific cards
            for event_card in soup.select('.event-card, tr'):
                name_el = event_card.select_one('.event-title, a[href*="/events/"]')
                venue_el = event_card.select_one('.venue-name, td:nth-child(2)')
                date_el = event_card.select_one('.event-date, td:nth-child(7)')
                
                if name_el and venue_el and date_el:
                    name = name_el.text.strip()
                    venue = venue_el.text.strip()
                    date_str = date_el.text.strip()
                    link = "https://www.freshtix.com" + name_el['href'] if name_el.has_attr('href') else "https://www.freshtix.com"
                    
                    try:
                        # Parsing "Sat, January 24, 2026"
                        clean_date = datetime.strptime(date_str.split('-')[0].strip(), "%a, %B %d, %Y").date()
                        events.append({
                            "id": f"ftix-{clean_date}-{name[:10].lower().replace(' ', '')}",
                            "name": name,
                            "venue": venue,
                            "date": clean_date,
                            "url": link
                        })
                    except Exception:
                        continue
        except Exception as e:
            print(f"Error on page {page}: {e}")
    return events

def clean_and_sync():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Scrape dynamic data
        freshtix_events = scrape_freshtix()
        
        # 2. Clear old data (Optional: you can filter by venue if you want to keep Ticketmaster data)
        db.query(Event).delete()
        
        # 3. Add Freshtix data
        for e in freshtix_events:
            db.add(Event(tm_id=e['id'], name=e['name'], date_time=e['date'], venue_name=e['venue'], ticket_url=e['url']))
            
        # 4. Add Manual 529 data
        for item in VERIFIED_529_DATA:
            dt = datetime.strptime(item['date'], "%Y-%m-%d").date()
            db.add(Event(
                tm_id=f"man-529-{item['date']}",
                name=item['name'],
                date_time=dt,
                venue_name="529",
                ticket_url="https://529atlanta.com/calendar/"
            ))
            
        db.commit()
        print(f"[+] Sync complete. Added {len(freshtix_events)} Freshtix events and 529 manual dates.")
    except Exception as e:
        print(f"Sync error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clean_and_sync()