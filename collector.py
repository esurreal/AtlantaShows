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
CULT_SHOCK = "Culture Shock"
EASTERN = "The Eastern"
MASQ = "The Masquerade"

# CURRENT VERIFIED LIST: Added The Eastern (AXS / Zero Mile)
VERIFIED_DATA = {
    V529: [
        {"date": "2026-01-23", "name": "High On Fire (Night 1)"},
        {"date": "2026-01-24", "name": "High On Fire (Night 2)"}
    ],
    EARL: [
        {"date": "2026-01-16", "name": "Pissed Jeans"},
        {"date": "2026-03-05", "name": "Rivers of Nihil / Cynic"}
    ],
    BOGGS: [
        {"date": "2026-03-03", "name": "Temptress / Friendship Commanders"},
        {"date": "2026-03-06", "name": "Author & Punisher / King Yosef"}
    ],
    CULT_SHOCK: [
        {"date": "2026-01-18", "name": "Second Death / Cruel Bones"},
        {"date": "2026-03-20", "name": "Bullshit Detector / Antagonizers"}
    ],
    # NEW: The Eastern Highlights (AXS)
    EASTERN: [
        {"date": "2026-01-29", "name": "The Wood Brothers"},
        {"date": "2026-02-27", "name": "STS9 (Night 1)"},
        {"date": "2026-02-28", "name": "STS9 (Night 2)"},
        {"date": "2026-03-07", "name": "Machine Girl / Show Me The Body"},
        {"date": "2026-03-12", "name": "Cat Power (The Greatest 20th Anniversary)"},
        {"date": "2026-04-17", "name": "Acid Bath / Crowbar / Eyehategod"}
    ],
    MASQ: [
        {"date": "2026-02-19", "name": "clipping. / Open Mike Eagle"}
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
        print("[*] Rebuilding database with The Eastern...")
        tm_list = fetch_ticketmaster()
        db.query(Event).delete()
        
        today = date.today()

        for e in tm_list:
            event_date = datetime.strptime(e['date'], "%Y-%m-%d").date()
            if event_date < today: continue
            # Exclude manual venues to prevent AXS/TM duplicate mess
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
            
            for item in shows:
                dt = datetime.strptime(item['date'], "%Y-%m-%d").date()
                if dt < today: continue
                db.add(Event(
                    tm_id=f"man-{venue[:3].lower()}-{item['date']}-{item['name'][:5].lower()}",
                    name=item['name'],
                    date_time=dt,
                    venue_name=venue,
                    ticket_url=link
                ))
        db.commit()
        print("[+] Sync complete! The Eastern is live.")
    finally:
        db.close()

if __name__ == "__main__":
    clean_and_sync()