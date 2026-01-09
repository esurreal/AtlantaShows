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

BOGGS = "Boggs Social & Supply"
EARL = "The EARL"
V529 = "529"
CULT_SHOCK = "Culture Shock"
EASTERN = "The Eastern"
MASQ = "The Masquerade"

# UPDATED VERIFIED LIST: Full 529, Boggs, and Culture Shock restoration
VERIFIED_DATA = {
    V529: [
        {"date": "2026-01-08", "name": "Downbeats & Distortions"},
        {"date": "2026-01-09", "name": "The Taj Motel Trio"},
        {"date": "2026-01-15", "name": "Elysium / After All This / Winder"},
        {"date": "2026-01-18", "name": "The Warsaw Clinic"},
        {"date": "2026-01-19", "name": "Anti-Sapien / Borzoi / Sewage Bath"},
        {"date": "2026-01-20", "name": "ENMY / Softspoken / Summer Hoop"},
        {"date": "2026-01-23", "name": "High On Fire (Night 1)"},
        {"date": "2026-01-24", "name": "High On Fire (Night 2)"},
        {"date": "2026-01-29", "name": "Graveyard Hours / Triangle Fire"},
        {"date": "2026-01-31", "name": "Too Hot for Leather (Metal Tribute)"},
        {"date": "2026-02-06", "name": "Parachutes / Tiny Banshee"},
        {"date": "2026-02-28", "name": "Yosemite In Black / Resistor"},
        {"date": "2026-03-01", "name": "Vicious Rumors / Paladin / Jaeger"}
    ],
    EARL: [
        {"date": "2026-01-16", "name": "Pissed Jeans"},
        {"date": "2026-01-21", "name": "Shiner"},
        {"date": "2026-01-24", "name": "Vio-lence / Deceased"},
        {"date": "2026-03-05", "name": "Rivers of Nihil / Cynic"}
    ],
    BOGGS: [
        {"date": "2026-01-09", "name": "ozello / Kyle Lewis / Yankee Roses"},
        {"date": "2026-01-10", "name": "Elijah Cruise / MENU / Dogwood"},
        {"date": "2026-01-17", "name": "The Carolyn / Knives / Wes Hoffman"},
        {"date": "2026-01-23", "name": "Empty Parking Lot / Lqm / Outfield Clovers"},
        {"date": "2026-01-31", "name": "Palaces / Muelas / Leafblower"},
        {"date": "2026-02-05", "name": "Ritual Arcana (Wino)"},
        {"date": "2026-02-06", "name": "Atoll / Truckstop Dickpill"},
        {"date": "2026-02-07", "name": "Temple of Love / Black Fractal"},
        {"date": "2026-03-03", "name": "Temptress / Friendship Commanders"},
        {"date": "2026-03-06", "name": "Author & Punisher / King Yosef"}
    ],
    CULT_SHOCK: [
        {"date": "2026-01-18", "name": "Second Death / Cruel Bones"},
        {"date": "2026-01-31", "name": "Los Ojos Muertos"},
        {"date": "2026-02-20", "name": "SinThya / Endeavor Into the Dark"},
        {"date": "2026-03-14", "name": "SinThya (Return Show)"},
        {"date": "2026-03-20", "name": "Bullshit Detector / Antagonizers"}
    ],
    EASTERN: [
        {"date": "2026-03-07", "name": "Machine Girl / Show Me The Body"},
        {"date": "2026-04-17", "name": "Acid Bath / Crowbar / Eyehategod"}
    ],
    MASQ: [
        {"date": "2026-02-19", "name": "clipping. / Open Mike Eagle (Heaven)"}
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
        print("[*] Performing Master Sync (Restoring 529, Boggs, and Culture Shock)...")
        tm_list = fetch_ticketmaster()
        db.query(Event).delete()
        
        today = date.today()

        for e in tm_list:
            event_date = datetime.strptime(e['date'], "%Y-%m-%d").date()
            if event_date < today: continue
            if any(v.lower() in e['venue'].lower() for v in ["boggs", "the earl", "529", "culture shock", "the eastern"]):
                continue
            db.add(Event(tm_id=e['id'], name=e['name'], date_time=event_date, venue_name=e['venue'], ticket_url=e['url']))
        
        for venue, shows in VERIFIED_DATA.items():
            link = "https://www.freshtix.com"
            if venue == V529: link = "https://529atlanta.com/calendar/"
            if venue == EARL: link = "https://badearl.freshtix.com/"
            if venue == BOGGS: link = "https://www.freshtix.com/organizations/arippinproduction"
            if venue == CULT_SHOCK: link = "https://www.venuepilot.co/events/cultureshock"
            if venue == EASTERN: link = "https://www.easternatl.com/calendar/"
            if venue == MASQ: link = "https://www.masqueradeatlanta.com/events/"
            
            for item in shows:
                dt = datetime.strptime(item['date'], "%Y-%m-%d").date()
                if dt < today: continue
                db.add(Event(
                    tm_id=f"man-{venue[:3].lower()}-{item['date']}-{item['name'][:5].lower().replace(' ', '')}",
                    name=item['name'],
                    date_time=dt,
                    venue_name=venue,
                    ticket_url=link
                ))
        db.commit()
        print("[+] Sync complete! All venues and shows are current.")
    finally:
        db.close()

if __name__ == "__main__":
    clean_and_sync()