from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# Get the database URL from Railway's environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the table structure for your concert events
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    tm_id = Column(String, unique=True, index=True) # Ticketmaster's unique ID
    name = Column(String, index=True)
    date_time = Column(DateTime)
    venue_name = Column(String)
    ticket_url = Column(String)

# Call this once to create the table if it doesn't exist
def init_db():
    Base.metadata.create_all(bind=engine)