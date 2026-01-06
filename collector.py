import os
import time
import requests
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

# VENUES WE MANUALLY PROTECT & UPDATE
MANUAL_VENUES = ["529", "The EARL", "Boggs Social", "Boggs Social Supply"]

VERIFIED_DATA = {
    "529": [
        {"date": "2026-01-18", "name": "The Warsaw Clinic (Dirty Holly, Grudgestep)"},
        {"date": "2026-01-19", "name": "Anti-Sapien (Borzoi, Feel Visit, Sewage Bath)"},
        {"date": "2026-01-20", "name": "ENMY (Softspoken, Summer Hoop)"},
        {"date": "2026-01-22", "name": "SUMPP (Local Support)"},
        {"date": "2026-01-23", "name": "High On Fire (w/ Hot Ram, Cheap Cigar)"},
        {"date": "2026-01-24", "name": "High On Fire (w/ Apostle, Big Oaf)"},
        {"date": "2026-01-29", "name": "Graveyard Hours (w/ Triangle Fire, Rosa Asphyxia)"},
        {"date": "2026-01-30", "name": "Joshua Quimby (Solo)"},
        {"date": "2026-01-31", "name": "Too Hot For Leather (Yevara, Vices of Vanity)"}
    ],
    "The EARL": [
        {"date": "2026-01-24", "name": "Vio-lence / Deceased / Nunslaughter"},
        {"date": "2026-02-06", "name": "Matt Pryor (The Get Up Kids)"}
    ],
    "Boggs Social": [
        {"date": "2026-01-31", "name": "Palaces / Muelas / Leafblower"},
        {"date": "2026-02-05", "name": "Ritual Arcana (Wino, SharLee LuckyFree)"},
        {"date": "2026-02-06", "name": "Atoll / Truckstop Dickpill / Squelching"},
        {"date": "2026-02-12", "name": "Primeval Well"}
    ]
}

def fetch_ticketmaster():
    """Attempt to pull the latest from TM if an API key exists."""
    api_key = os.getenv("TM_API_KEY")
    if not api_key:
        return []
    
    url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={api_key}&city=Atlanta&classificationName=music&size=50"
    try:
        r = requests.get(url)
        data = r.json()
        tm_events = []
        for e in data.get('_embedded', {}).get('events', []):
            tm_events.append({
                "id": e['id'],
                "name": e['name'],
                "date": e['dates']['start']['localDate'],
                "venue": e['_embedded']['venues'][0]['name'],
                "url": e['url']
            })
        return tm_events
    except:
        return []

def clean_and_sync():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("[*] Refreshing schedules...")
        
        # 1. Fetch Ticketmaster data
        tm_list = fetch_ticketmaster()
        
        # 2. CLEAR ONLY THE MANUAL VENUES (prevents duplicates while keeping TM data)
        db.query(Event).filter(Event.venue_name.in_(MANUAL_VENUES)).delete(synchronize_session=False)
        
        # 3. Add Verified Manual Data
        for venue, shows in VERIFIED_DATA.items():
            links = {
                "Boggs Social": "https://www.freshtix.com/organizations/boggs-social--supply",
                "529": "https://529atlanta.com/calendar/",
                "The EARL": "https://badearl.freshtix.com/"
            }
            for item in shows:
                dt = datetime.strptime(item['date'], "%Y-%m-%d").date()
                db.add(Event(
                    tm_id=f"man-{venue[:3]}-{item['date']}",
                    name=item['name'],
                    date_time=dt,
                    venue_name=venue,
                    ticket_url=links.get(venue, "")
                ))
        
        # 4. Add TM data (only if not already there)
        for e in tm_list:
            existing = db.query(Event).filter(Event.tm_id == e['id']).first()
            if not existing:
                db.add(Event(
                    tm_id=e['id'],
                    name=e['name'],
                    date_time=datetime.strptime(e['date'], "%Y-%m-%d").date(),
                    venue_name=e['venue'],
                    ticket_url=e['url']
                ))

        db.commit()
        print("[+] Database synced: Ticketmaster + Manual venues are live.")
    finally:
        db.close()

if __name__ == "__main__":
    clean_and_sync()