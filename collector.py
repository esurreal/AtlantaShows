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

# Data we manually verified from your uploaded screenshot
VERIFIED_529_DATA = [
    {"date": "2026-01-23", "name": "High On Fire (w/ Hot Ram, Cheap Cigar)"},
    {"date": "2026-01-24", "name": "High On Fire (w/ Apostle, Big Oaf)"},
    {"date": "2026-01-29", "name": "Graveyard Hours (w/ Triangle Fire)"},
    {"date": "2026-01-31", "name": "Too Hot For Leather (w/ Vices of Vanity)"}
]

def sync_verified_data():
    print("[*] Syncing verified data from screenshot...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    added = 0
    try:
        for item in VERIFIED_529_DATA:
            dt = datetime.strptime(item['date'], "%Y-%m-%d").date()
            unique_id = f"529-{item['date']}-manual"
            
            existing = db.query(Event).filter_by(tm_id=unique_id).first()
            if not existing:
                db.add(Event(
                    tm_id=unique_id,
                    name=item['name'],
                    date_time=dt,
                    venue_name="529",
                    ticket_url="https://529atlanta.com/calendar/"
                ))
                added += 1
        db.commit()
        print(f"[+] Added {added} new verified shows.")
    finally:
        db.close()

if __name__ == "__main__":
    # In a real scenario, you'd add your Boggs/Earl scrapers here too
    sync_verified_data()