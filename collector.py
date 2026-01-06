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
        {"date": "2026-01-03", "name": "Edwin & My Folks (w/ Rahbi, Hannah)"},
        {"date": "2026-01-04", "name": "Fatal Attraction (Metal Night)"},
        {"date": "2026-01-08", "name": "Downbeats & Distortions (Lovehex, Nitsirt)"},
        {"date": "2026-01-09", "name": "The Taj Motel Trio (Analog Day Dream)"},
        {"date": "2026-01-10", "name": "Nick Nasty (Close To Midnight)"},
        {"date": "2026-01-14", "name": "The Cosmic Mic (Open Mic)"},
        {"date": "2026-01-15", "name": "Elysium / After All This / Winder"},
        {"date": "2026-01-16", "name": "Phamily & Friends Tour"},
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
        {"date": "2026-01-09", "name": "Numbers Station Records Showcase"},
        {"date": "2026-01-10", "name": "Gringo Star (The Sporrs, Lowtown)"},
        {"date": "2026-01-11", "name": "The Last Revel (Wilson Springs Hotel Duo)"},
        {"date": "2026-01-15", "name": "Rod Hamdallah (Chester Lethers)"},
        {"date": "2026-01-16", "name": "Pissed Jeans (Morgan Garrett, Chaos OK)"},
        {"date": "2026-01-17", "name": "Country Westerns (Ultra Lights)"},
        {"date": "2026-01-19", "name": "Modern Nature (Brigid Dawson)"},
        {"date": "2026-01-20", "name": "Friendship (Little Mazarn)"},
        {"date": "2026-01-21", "name": "Shiner (Dropsonic, Bursting)"},
        {"date": "2026-01-22", "name": "Off With Their Heads"},
        {"date": "2026-01-23", "name": "Sean Rowe"},
        {"date": "2026-01-24", "name": "Vio-lence / Deceased / Nunslaughter"},
        {"date": "2026-01-25", "name": "Low Water Bridge Band"},
        {"date": "2026-01-30", "name": "God Bullies (Vincas, Rubber Udder)"},
        {"date": "2026-01-31", "name": "K Michelle Dubois (Gouwzee)"},
        {"date": "2026-02-06", "name": "Matt Pryor (The Get Up Kids)"}
    ],
    BOGGS: [
        {"date": "2026-01-07", "name": "Karaoke Night w/ Music Mike"},
        {"date": "2026-01-09", "name": "Ozello / Kyle Lewis / Yankee Roses"},
        {"date": "2026-01-10", "name": "Elijah Cruise / MENU / Dogwood"},
        {"date": "2026-01-13", "name": "Socially Awkward Comedy (Open Mic)"},
        {"date": "2026-01-14", "name": "Karaoke Night w/ Music Mike"},
        {"date": "2026-01-16", "name": "SPUTNIK! Dark Alternative Music Video Night"},
        {"date": "2026-01-17", "name": "The Carolyn / Knives / Wes Hoffman"},
        {"date": "2026-01-21", "name": "Karaoke Night w/ Music Mike"},
        {"date": "2026-01-22", "name": "Barreracuda Presents: House of Flops"},
        {"date": "2026-01-23", "name": "Empty Parking Lot / Lqm / Outfield Clovers"},
        {"date": "2026-01-24", "name": "Harnessed: January Edition (Queer Nightlife)"},
        {"date": "2026-01-25", "name": "SUPER SMASH BREWS! Melee Tournament"},
        {"date": "2026-01-28", "name": "Karaoke Night w/ Music Mike"},
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
            if any(v.lower() in e['venue'].lower() for v in ["boggs", "the earl", "529"]):
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
            if venue == EARL: link = "https://badearl.freshtix.com/"
            
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