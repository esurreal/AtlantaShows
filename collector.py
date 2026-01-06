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

# CONSOLIDATED VERIFIED DATA
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
        {"date": "2026-01-15", "name": "Rod Hamdallah w/ Chester Lethers"},
        {"date": "2026-01-16", "name": "Pissed Jeans"},
        {"date": "2026-01-17", "name": "Country Westerns + Ultra Lights"},
        {"date": "2026-01-19", "name": "Modern Nature"},
        {"date": "2026-01-20", "name": "Friendship"},
        {"date": "2026-01-22", "name": "Off With Their Heads"},
        {"date": "2026-01-23", "name": "Sean Rowe"},
        {"date": "2026-01-24", "name": "Nunslaughter / Vio-lence / Deceased"},
        {"date": "2026-01-31", "name": "K Michelle Dubois"},
        {"date": "2026-02-05", "name": "Taper's Choice"},
        {"date": "2026-02-06", "name": "Matt Pryor (The Get Up Kids)"}
    ],
    "Boggs Social": [
        {"date": "2026-01-09", "name": "Ozello / Kyle Lewis / Yankee Roses"},
        {"date": "2026-01-10", "name": "Elijah Cruise / MENU / Dogwood"},
        {"date": "2026-01-17", "name": "The Carolyn / Knives / Wes Hoffman"},
        {"date": "2026-01-23", "name": "Empty Parking Lot / Lqm / The Outfield Clovers"},
        {"date": "2026-01-31", "name": "Palaces / Muelas / Leafblower"},
        {"date": "2026-02-05", "name": "Ritual Arcana (Wino, SharLee LuckyFree)"},
        {"date": "2026-02-06", "name": "Atoll / Truckstop Dickpill / Squelching"},
        {"date": "2026-02-07", "name": "Temple of Love / Black Fractal / Drugula"}
    ]
}

def clean_and_sync():
    print("[*] Rebuilding schedule with manual verified data...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Clear existing data to ensure no duplicates
        db.query(Event).delete()
        
        for venue, shows in VERIFIED_DATA.items():
            # Setup ticket links
            links = {
                "Boggs Social": "https://www.freshtix.com/organizations/boggs-social--supply",
                "529": "https://529atlanta.com/calendar/",
                "The EARL": "https://badearl.freshtix.com/"
            }
            
            for item in shows:
                dt = datetime.strptime(item['date'], "%Y-%m-%d").date()
                # Create a clean ID: date + first 5 of venue + first 5 of name
                unique_id = f"{item['date']}-{venue[:5].lower()}-{item['name'][:5].lower()}"
                
                db.add(Event(
                    tm_id=unique_id,
                    name=item['name'],
                    date_time=dt,
                    venue_name=venue,
                    ticket_url=links.get(venue, "")
                ))
        db.commit()
        print("[+] All venues synced.")
    except Exception as e:
        print(f"Sync error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clean_and_sync()