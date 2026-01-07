import os
import requests
from datetime import datetime, date
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

# UPDATED: Added Author & Punisher + Full Spring Schedule
VERIFIED_DATA = {
    V529: [
        {"date": "2026-01-08", "name": "Downbeats & Distortions"},
        {"date": "2026-01-09", "name": "The Taj Motel Trio"},
        {"date": "2026-01-23", "name": "High On Fire (Night 1)"},
        {"date": "2026-01-24", "name": "High On Fire (Night 2)"}
    ],
    EARL: [
        {"date": "2026-01-16", "name": "Pissed Jeans"},
        {"date": "2026-01-21", "name": "Shiner"},
        {"date": "2026-01-24", "name": "Vio-lence / Deceased"},
        {"date": "2026-02-06", "name": "Matt Pryor (The Get Up Kids)"},
        {"date": "2026-03-05", "name": "Rivers of Nihil"}
    ],
    BOGGS: [
        {"date": "2026-01-09", "name": "Ozello / Kyle Lewis / Yankee Roses"},
        {"date": "2026-01-10", "name": "Elijah Cruise / MENU / Dogwood"},
        {"date": "2026-01-17", "name": "The Carolyn / Knives / Wes Hoffman"},
        {"date": "2026-01-31", "name": "Palaces / Muelas / Leafblower"},
        {"date": "2026-02-05", "name": "Ritual Arcana (Wino)"},
        {"date": "2026-02-06", "name": "Atoll / Truckstop Dickpill"},
        {"date": "2026-02-07", "name": "Temple of Love / Black Fractal"},
        {"date": "2026-02-28", "name": "Doesin / Star Funeral"},
        {"date": "2026-03-03", "name": "Temptress / Friendship Commanders"},
        {"date": "2026-03-06", "name": "Author & Punisher / King Yosef / Black Magnet"} # Fixed!
    ]
}

def fetch_ticketmaster():
    api_key = os.getenv("TM_API_KEY")
    if not api_key: 
        print("[!] No Ticketmaster API Key found.")
        return []
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
        print("[*] Starting sync...")
        tm_list = fetch_ticketmaster()
        print(f"[*] Found {len(tm_list)} shows on Ticketmaster.")
        
        # Clear database to prevent duplicates
        db.query(Event).delete()
        
        today = date.today()

        # Add Ticketmaster shows (The Tabernacle, Masquerade, etc)
        for e in tm_list:
            event_date = datetime.strptime(e['date'], "%Y-%m-%d").date()
            if event_date < today: continue
            # Don't let TM override our manual venue list (TM is often wrong about Earl/Boggs links)
            if any(v.lower() in e['venue'].lower() for v in ["boggs", "the earl", "529"]):
                continue
            db.add(Event(tm_id=e['id'], name=e['name'], date_time=event_date, venue_name=e['venue'], ticket_url=e['url']))
        
        # Add our high-quality Verified List
        for venue, shows in VERIFIED_DATA.items():
            link = "https://www.freshtix.com"
            if venue == V529: link = "https://529atlanta.com/calendar/"
            if venue == EARL: link = "https://badearl.freshtix.com/"
            if venue == BOGGS: link = "https://www.freshtix.com/organizations/arippinproduction"
            
            for item in shows:
                dt = datetime.strptime(item['date'], "%Y-%m-%d").date()
                if dt < today: continue
                
                # Create a unique ID for manual entries
                manual_id = f"man-{venue[:3].lower()}-{item['date']}-{item['name'][:5].replace(' ', '').lower()}"
                
                db.add(Event(
                    tm_id=manual_id,
                    name=item['name'],
                    date_time=dt,
                    venue_name=venue,
                    ticket_url=link
                ))
        
        db.commit()
        print("[+] Sync complete. Database is up to date.")
    finally:
        db.close()

if __name__ == "__main__":
    clean_and_sync()