import requests
from bs4 import BeautifulSoup
from datetime import datetime

def scrape_the_earl():
    print("--- 2c. Scraping The Earl (EAV) via BeautifulSoup... ---")
    url = "https://www.badearl.com/show-listings"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        events = []

        # The Earl uses 'event-info-wrapper' for their shows
        show_containers = soup.find_all('div', class_='event-info-wrapper')

        for show in show_containers:
            name_tag = show.find('h1', class_='event-title')
            name = name_tag.get_text(strip=True) if name_tag else "Unknown Artist"

            date_tag = show.find('span', class_='event-date')
            date_str = date_tag.get_text(strip=True) if date_tag else None
            
            event_date = None
            if date_str:
                try:
                    # Formats "Dec 20" to a date object for the current year
                    current_year = datetime.now().year
                    event_date = datetime.strptime(f"{date_str} {current_year}", "%b %d %Y").date()
                except Exception as e:
                    print(f"Date error for {name}: {e}")

            # Create a unique ID for our database
            clean_id = f"earl_{name.lower().replace(' ', '_')}_{date_str}"

            events.append({
                "tm_id": clean_id,
                "name": name,
                "date_time": event_date,
                "venue_name": "The Earl",
                "ticket_url": url 
            })
            
        return events
    except Exception as e:
        print(f"Error scraping The Earl: {e}")
        return []