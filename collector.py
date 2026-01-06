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

VERIFIED_529_DATA = [
    {"date": "2026-01-23", "name": "High On Fire (w/ Hot Ram, Cheap Cigar)"},
    {"date": "2026-01-24", "name": "High On Fire (w/ Apostle, Big Oaf)"},
    {"date": "2026-01-29", "name": "Graveyard Hours (w/ Triangle Fire, Rosa Asphyxia)"},
    {"date": "2026-01-30", "name": "Joshua Quimby (Solo)"},
    {"date": "2026-01-31", "name": "Too Hot For Leather (Yevara, Vices of Vanity)"}
]

def clean_and_sync():
    print("[*] Merging lineups and cleaning 529...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Clear out old/messy 529 data
        db.query(Event).filter(Event.venue_name == "529").delete()
        
        for item in VERIFIED_529_DATA:
            dt = datetime.strptime(item['date'], "%Y-%m-%d").date()
            unique_id = f"v529-{item['date']}"
            db.add(Event(
                tm_id=unique_id,
                name=item['name'],
                date_time=dt,
                venue_name="529",
                ticket_url="https://529atlanta.com/calendar/"
            ))
        db.commit()
    except Exception as e:
        print(f"Sync error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    time.sleep(2)
    clean_and_sync()