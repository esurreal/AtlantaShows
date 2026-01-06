import os
from sqlalchemy import create_engine, Column, String, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# --- Database Config ---
Base = declarative_base()
class Event(Base):
    __tablename__ = 'events'
    tm_id = Column(String, primary_key=True)
    name = Column(String)
    date_time = Column(Date)
    venue_name = Column(String)
    ticket_url = Column(Text)

# Use your Railway Database URL
raw_db_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL", "sqlite:///shows.db")
db_url = raw_db_url.replace("postgres://", "postgresql://", 1) if "postgres://" in raw_db_url else raw_db_url
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

# --- Verified Data from Screenshot ---
VERIFIED_SHOWS = [
    {"date": "2026-01-18", "name": "The Warsaw Clinic", "lineup": "Dirty Holly, Grudgestep"},
    {"date": "2026-01-19", "name": "Anti-Sapien", "lineup": "Borzoi, Feel Visit, Sewage Bath"},
    {"date": "2026-01-20", "name": "ENMY", "lineup": "Softspoken, Summer Hoop"},
    {"date": "2026-01-22", "name": "SUMPP", "lineup": "Local Support"},
    {"date": "2026-01-23", "name": "HIGH ON FIRE", "lineup": "HOT RAM, Cheap Cigar"},
    {"date": "2026-01-24", "name": "HIGH ON FIRE", "lineup": "Apostle, Big Oaf"},
    {"date": "2026-01-29", "name": "Graveyard Hours", "lineup": "Triangle Fire, Rosa Asphyxia"},
    {"date": "2026-01-30", "name": "Joshua Quimby", "lineup": "Solo"},
    {"date": "2026-01-31", "name": "Too Hot For Leather", "lineup": "Yevara, Vices of Vanity"}
]

def inject():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    count = 0
    try:
        for show in VERIFIED_SHOWS:
            show_date = datetime.strptime(show['date'], "%Y-%m-%d").date()
            # Unique ID based on date and name
            unique_id = f"529-{show['date']}-{show['name'][:5].lower().replace(' ', '')}"
            
            existing = db.query(Event).filter_by(tm_id=unique_id).first()
            if not existing:
                new_event = Event(
                    tm_id=unique_id,
                    name=f"{show['name']} ({show['lineup']})",
                    date_time=show_date,
                    venue_name="529",
                    ticket_url="https://529atlanta.com/calendar/"
                )
                db.add(new_event)
                count += 1
        db.commit()
        print(f"--- SUCCESS: Injected {count} verified shows from 529 calendar image. ---")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inject()