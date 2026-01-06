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

# Standardize names
BOGGS = "Boggs Social & Supply"
EARL = "The EARL"
V529 = "529"

VERIFIED_DATA = {
    V529: [
        {"date": "2026-01-08", "name": "Downbeats & Distortions (Lovehex, Nitsirt)"},
        {"date": "2026-01-09", "name": "The Taj Motel Trio (Analog Day Dream, Stepmoms)"},
        {"date": "2026-01-10", "name": "Nick Nasty (Close To Midnight, Heroes For Ghosts)"},
        {"date": "2026-01-14", "name": "The Cosmic Mic (Open Mic)"},
        {"date": "2026-01-15", "name": "Elysium / After All This / Winder"},
        {"date": "2026-01-16", "name": "Phamily & Friends Tour (Unfaced Ree, Veda Janee)"},
        {"date": "2026-01-17", "name": "Kado Dupré (Chris Harry, Mattie B)"},
        {"date": "2026-01-18", "name": "The Warsaw Clinic (Dirty Holly, Grudgestep)"},
        {"date": "2026-01-19", "name": "Anti-Sapien (Borzoi, Feel Visit, Sewage Bath)"},
        {"date": "2026-01-20", "name": "ENMY (Softspoken, Summer Hoop)"},
        {"date": "2026-01-22", "name": "SUMPP (Local Support)"},
        {"date": "2026-01-23", "name": "High On Fire (Night 1 w/ Hot Ram)"},
        {"date": "2026-01-24", "name": "High On Fire (Night 2 w/ Apostle)"},
        {"date": "2026-01-29", "name": "Graveyard Hours (w/ Triangle Fire)"},
        {"date": "2026-01-30", "name": "Joshua Quimby (Solo)"},
        {"date": "2026-01-31", "name": "Too Hot For Leather (Yevara, Vices of Vanity)"}
    ],
    EARL: [
        {"date": "2026-01-24", "name": "Vio-lence / Deceased / Nunslaughter"},
        {"date": "2026-02-06", "name": "Matt Pryor (The Get Up Kids)"}
    ],
    BOGGS: [
        {"date": "2026-01-09", "name": "Ozello / Kyle Lewis / Yankee Roses"},
        {"date": "2026-01-10", "name": "Elijah Cruise / MENU / Dogwood"},
        {"date": "2026-01-17", "name": "The Carolyn / Knives / Wes Hoffman"},
        {"date": "2026-01-23", "name": "Empty Parking Lot / Lqm"},
        {"date": "2026-01-31", "name": "Palaces / Muelas / Leafblower"},
        {"date": "2026-02-05", "name": "Ritual Arcana (Wino, SharLee LuckyFree)"},
        {"date": "2026-02-06", "name": "Atoll / Truckstop Dickpill / Squelching"},
        {"date": "2026-02-12", "name": "Primeval Well"}
    ]
}

def fetch_ticketmaster():
    api_key = os.getenv("TM_API_KEY")
    if not api_key: return []
    url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={api_key}&city=Atlanta&classificationName=music&size=100"
    try:
        r = requests.get(url)
        data = r.json()
        return [{
            "id": e['id'],
            "name": e['name'],
            "date": e['dates']['start']['localDate'],
            "venue": e['_embedded']['venues'][0]['name'],
            "url": e['url']
        } for e in data.get('_embedded', {}).get('events', [])]
    except: return []

def clean_and_sync():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("[*] Rebuilding database with full January schedules...")
        tm_list = fetch_ticketmaster()
        db.query(Event).delete()
        
        # Add Ticketmaster (skipping manual venue overlaps)
        for e in tm_list:
            if any(v.lower() in e['venue'].lower() for v in ["Boggs", "The Earl", "529"]):
                continue
            db.add(Event(
                tm_id=e['id'],
                name=e['name'],
                date_time=datetime.strptime(e['date'], "%Y-%m-%d").date(),
                venue_name=e['venue'],
                ticket_url=e['url']
            ))
        
        # Add Manual Verified Data
        for venue, shows in VERIFIED_DATA.items():
            link = "https://www.freshtix.com"
            if venue == V529: link = "https://529atlanta.com/calendar/"
            
            for item in shows:
                dt = datetime.strptime(item['date'], "%Y-%m-%d").date()
                db.add(Event(
                    tm_id=f"man-{venue[:3].lower()}-{item['date']}-{item['name'][:5].lower()}",
                    name=item['name'],
                    date_time=dt,
                    venue_name=venue,
                    ticket_url=link
                ))
        db.commit()
        print("[+] Sync complete.")
    finally:
        db.close()

if __name__ == "__main__":
    clean_and_sync()