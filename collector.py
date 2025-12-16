import requests
from datetime import datetime
from database import AsyncSessionLocal, Event, init_db
import os

# Ensure the database table exists
init_db()

TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")
BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

async def fetch_and_save_events():
    """Fetches events from Ticketmaster and saves/updates them in the database."""
    print("Starting Ticketmaster data collection...")
    
    params = {
        'apikey': TICKETMASTER_API_KEY,
        'city': 'Atlanta',
        'stateCode': 'GA',
        'segmentName': 'Music',
        'size': 200,
        'sort': 'date,asc'
    }

    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        events_data = data.get('_embedded', {}).get('events', [])
        async with AsyncSessionLocal() as session:
        
            for event in events_data:
                tm_id = event.get('id')
                event_name = event.get('name')
                
                # Use localDateTime for event time
                date_time_str = event.get('dates', {}).get('start', {}).get('localDateTime')
                date_time = datetime.fromisoformat(date_time_str) if date_time_str else None
                
                venue = event.get('_embedded', {}).get('venues', [{}])[0]
                venue_name = venue.get('name')
                ticket_url = event.get('url')

                # Check if the event already exists (to prevent duplicates)
                existing_event = session.query(Event).filter(Event.tm_id == tm_id).first()

            if existing_event:
                # Update existing event data
                existing_event.name = event_name
                existing_event.date_time = date_time
                existing_event.venue_name = venue_name
                existing_event.ticket_url = ticket_url
            else:
                # Create new event
                new_event = Event(
                    tm_id=tm_id,
                    name=event_name,
                    date_time=date_time,
                    venue_name=venue_name,
                    ticket_url=ticket_url
                )
                session.add(new_event)

        session.commit()
        session.close()
        print(f"Successfully collected and updated {len(events_data)} events.")

    except Exception as e:
        print(f"An error occurred during data collection: {e}")

if __name__ == "__main__":
    fetch_and_save_events()