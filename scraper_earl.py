import json
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

def scrape_the_earl():
    events = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        # Using the primary verified Bandsintown URL for The Earl
        url = "https://www.bandsintown.com/v/10001781-the-earl"
        
        try:
            # wait_until="commit" is the fastest way to get in before ads load
            page.goto(url, wait_until="commit", timeout=60000)
            
            # Script tags are metadata, so we wait for 'attached' state
            page.wait_for_selector('script[type="application/ld+json"]', state="attached", timeout=15000)
            
            scripts = page.locator('script[type="application/ld+json"]').all()

            for script in scripts:
                try:
                    content = script.evaluate("node => node.textContent").strip()
                    if not content: continue
                    
                    data = json.loads(content)
                    
                    # Handle lists, single objects, and nested @graph structures
                    potential_items = []
                    if isinstance(data, list):
                        potential_items = data
                    elif isinstance(data, dict):
                        potential_items = data.get('@graph', [data])

                    for item in potential_items:
                        if not isinstance(item, dict): continue
                        
                        # Valid concerts always have a startDate
                        if 'startDate' in item:
                            name = item.get('name', '')
                            start_date_str = item.get('startDate', '')
                            tix_url = item.get('url', url)
                            
                            if not name or not start_date_str:
                                continue

                            # Parse Date
                            clean_date_str = start_date_str.split('T')[0]
                            dt_obj = datetime.strptime(clean_date_str, "%Y-%m-%d")
                            event_date = dt_obj.date()

                            # Final Name Cleanup
                            # Removes "@ The EARL", "at The EARL", and "The EARL presents"
                            clean_name = re.sub(r'(\s*@\s*The\s*EARL.*|\s+at\s+The\s+EARL.*)', '', name, flags=re.I).strip()
                            clean_name = re.sub(r'^The\s+EARL\s+presents[:\s]+', '', clean_name, flags=re.I).strip()

                            if clean_name.upper() == "THE EARL" or len(clean_name) < 2:
                                continue

                            events.append({
                                "tm_id": f"earl-{event_date}-{clean_name.lower().replace(' ', '')[:15]}",
                                "name": clean_name,
                                "date_time": event_date,
                                "venue_name": "The Earl",
                                "ticket_url": tix_url
                            })
                except:
                    continue

        except Exception as e:
            print(f"Bandsintown Sync error: {e}")
        finally:
            browser.close()
            
    # Deduplicate based on ID
    unique_events = {e['tm_id']: e for e in events}.values()
    return list(unique_events)

if __name__ == "__main__":
    for e in scrape_the_earl():
        print(f"{e['date_time']} | {e['name']}")