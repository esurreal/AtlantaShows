import requests
from bs4 import BeautifulSoup

def test_boggs_v4():
    url = "https://www.freshtix.com/organizations/arippinproduction"
    print(f"[*] Testing Version 4 (Universal) on: {url}...")
    
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for all links that have 'events' in the URL
        links = soup.find_all('a', href=True)
        
        found_count = 0
        for link in links:
            href = link['href']
            # Filter for event links and ignore the 'Find Tickets' buttons
            if '/events/' in href and "Find Tickets" not in link.text:
                title = link.text.strip()
                if not title: continue
                
                # To find the date, we look at the text inside the same parent container
                parent = link.find_parent('div')
                full_text = parent.get_text(separator='|').strip() if parent else ""
                
                # Fix the URL if it's relative
                full_url = href if href.startswith('http') else f"https://www.freshtix.com{href}"
                
                print(f"TITLE: {title}")
                print(f"EXTRACTED DATA: {full_text[:100]}...") # Show a snippet of the date info
                print(f"URL: {full_url}")
                print("-" * 30)
                found_count += 1
                
        if found_count == 0:
            print("[!] Still empty. Freshtix might be blocking the script or using Javascript to load the list.")

    except Exception as e:
        print(f"[X] Error: {e}")

if __name__ == "__main__":
    test_boggs_v4()