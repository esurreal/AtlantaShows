import os
import time
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

# Verified data from BOTH screenshots
VERIFIED_DATA = {
    "529": [
        {"date": "2026-01-03", "name": "Edwin & My Folks (Rahbi, Hannah)"},
        {"date": "2026-01-08", "name": "Lovehex / Nibiru / JoshDidIt / 24 Skrappy / MillWave"},
        {"date": "2026-01-09", "name": "The Taj Motel Trio (Analog Day Dream, Left Hand Hotdog)"},
        {"date": "2026-01-10", "name": "Nick Nasty (Close To Midnight, Heroes For Ghosts)"},
        {"date": "2026-01-15", "name": "Elysium / After All This / Winder"},
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
    "Boggs Social": [
        {"date": "2026-01-07", "name": "Karaoke Night w/ Music Mike"},
        {"date": "2026-01-09", "name": "Ozello / Kyle Lewis / Yankee Roses"},
        {"date": "2026-01-10", "name": "Elijah Cruise / MENU / Dogwood / Parachutes"},
        {"date": "2026-01-13", "name": "Socially Awkward Comedy"},
        {"date": "2026-01-14", "name": "Karaoke Night w/ Music Mike"},
        {"date": "2026-01-16", "name": "SPUTNIK! Atlanta's Dark Alternative Music Video Night"},
        {"date": "2026-01-17", "name": "The Carolyn / Knives / Wes Hoffman / Breaux"},
        {"date": "2026-01-21", "name": "Karaoke Night w/ Music Mike"},
        {"date": "2026-01-22", "name": "BarreraCuda Presents: House of Flops"},
        {"date": "2026-01-23", "name": "Empty Parking Lot / Lqm / The Outfield Clovers"},
        {"date": "2026-01-24", "name": "Harnessed: January Edition"},
        {"date": "2026-01-25", "name": "Super Smash Brews! Melee Tournament"},
        {"date": "2026-01-28", "name": "Karaoke Night w/ Music Mike"},
        {"date": "2026-01-31", "name": "Palaces / Muelas / Leafblower"}
    ]
}

def clean_and_sync():
    print("[*] Rebuilding 529 and Boggs schedules...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Wipe existing rows for these two venues to avoid doubles
        db.query(Event).filter(Event.venue_name.in_(["529", "Boggs Social"])).delete(synchronize_session=False)
        
        for venue, shows in VERIFIED_DATA.items():
            link = "https://boggssocial.com/calendar" if venue == "Boggs Social" else "https://529atlanta.com/calendar/"
            for item in shows:
                dt = datetime.strptime(item['date'], "%Y-%m-%d").date()
                unique_id = f"v-{venue.lower()[:3]}-{item['date']}-{item['name'][:5].lower()}"
                db.add(Event(
                    tm_id=unique_id,
                    name=item['name'],
                    date_time=dt,
                    venue_name=venue,
                    ticket_url=link
                ))
        db.commit()
        print("[+] Database sync complete.")
    except Exception as e:
        print(f"Sync error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    time.sleep(2)
    clean_and_sync()