import os
import requests
import time
import urllib.parse
from datetime import datetime, date
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

# Database Setup
raw_db_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL", "sqlite:///shows.db")
db_url = raw_db_url.replace("postgres://", "postgresql://", 1) if "postgres://" in raw_db_url else raw_db_url
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

# Venue Constants
BOGGS = "Boggs Social & Supply"
EARL = "The EARL"
V529 = "529"
CULT_SHOCK = "Culture Shock"
EASTERN = "The Eastern"
MASQ = "The Masquerade"
T_WEST = "Terminal West"
VARIETY = "Variety Playhouse"

# ==========================================================
# MANUALLY VERIFIED SHOWS - KEPT AS REQUESTED
# ==========================================================
VERIFIED_DATA = {
    V529: [
        {"date": "2026-02-19", "name": "Anti-Sapien / Borzoi / Sewage Bath"},
        {"date": "2026-02-20", "name": "ENMY / Softspoken / Summer Hoop"},
        {"date": "2026-02-22", "name": "SUMPP"},
        {"date": "2026-02-23", "name": "High On Fire / Hot Ram (Night 1)"},
        {"date": "2026-02-24", "name": "High On Fire / Apostle (Night 2)"},
        {"date": "2026-02-29", "name": "Graveyard Hours / Triangle Fire"},
        {"date": "2026-03-01", "name": "Too Hot for Leather / Yevara"},
        {"date": "2026-03-06", "name": "Parachutes / Tiny Banshee"},
        {"date": "2026-03-13", "name": "Breaux / The Catastrophes"},
        {"date": "2026-03-21", "name": "DONEFOR / Red Hot Empty (Live Loud)"},
        {"date": "2026-05-02", "name": "Uada / Mortiis / Rome"}
    ],
    EARL: [
        {"date": "2026-02-20", "name": "True Blossom / Sleepers Club"},
        {"date": "2026-02-21", "name": "Nuovo Testamento / Dark Chisme"},
        {"date": "2026-02-22", "name": "Jake Xerxes Fussell / Dougie Poole"},
        {"date": "2026-02-24", "name": "Spiritual Cramp / Liberty and Justice"},
        {"date": "2026-02-26", "name": "Dyskrasia / Normal Bias"},
        {"date": "2026-02-27", "name": "The Constellations / Anthmz"},
        {"date": "2026-02-28", "name": "Prison Affair / RMBLR"},
        {"date": "2026-03-04", "name": "The Deslondes / Sabine McCalla"},
        {"date": "2026-03-12", "name": "Twen / Monsoon"},
        {"date": "2026-04-10", "name": "Redd Kross"},
        {"date": "2026-05-04", "name": "Flyte (Rescheduled)"}
    ],
    VARIETY: [
        {"date": "2026-02-20", "name": "Peter McPoland / Dug"},
        {"date": "2026-02-21", "name": "Marty Stuart / Hogslop String Band"},
        {"date": "2026-02-27", "name": "Big Head Todd and The Monsters"},
        {"date": "2026-02-28", "name": "Billy F. Gibbons & The BFG Band"},
        {"date": "2026-03-14", "name": "Wednesday / Gouge Away (Sold Out)"},
        {"date": "2026-03-21", "name": "Mike Gordon"},
        {"date": "2026-03-26", "name": "Cymande"},
        {"date": "2026-04-03", "name": "Indigo De Souza"},
        {"date": "2026-05-06", "name": "Ty Segall"},
        {"date": "2026-10-22", "name": "Benjamin Tod & The Inline Six"}
    ],
    BOGGS: [
        {"date": "2026-03-03", "name": "Temptress / Friendship Commanders", "url": "https://www.boggssocial.com/events/temptress-friendship-commanders"},
        {"date": "2026-03-06", "name": "Author & Punisher / King Yosef", "url": "https://www.boggssocial.com/events/author-punisher-at-boggs"},
        {"date": "2026-03-08", "name": "Palaces / Muelas / Leafblower", "url": "https://www.freshtix.com/events/arippinproduction"},
        {"date": "2026-03-10", "name": "Over Anna / Kat and the Hurricane / Parachutes", "url": "https://www.freshtix.com/events/arippinproduction"},
        {"date": "2026-04-03", "name": "MENU / Cascadent / Novumora / Backtoearth", "url": "https://www.freshtix.com/events/arippinproduction"},
        {"date": "2026-04-05", "name": "Cut Throat Freak Show / Fuckin Nothin / Horse Bre...", "url": "https://www.boggssocial.com/events/cut-throat-freak-show"},
        {"date": "2026-04-10", "name": "Gooseberry / Recess Party / Villareal", "url": "https://www.freshtix.com/events/arippinproduction"},
        {"date": "2026-05-02", "name": "RAVEN w/ Special Guests Slackjaw", "url": "https://www.freshtix.com/events/raven"},
        {"date": "2026-05-23", "name": "Atlanta Ska Night Volume 8!", "url": "https://www.freshtix.com/events/atlska8"}
    ],
    EASTERN: [
        {"date": "2026-02-25", "name": "Jesse Welles / S.G. Goodman"},
        {"date": "2026-02-27", "name": "STS9 w/ Lotus (Night 1)"},
        {"date": "2026-02-28", "name": "STS9 w/ Lotus (Night 2)"},
        {"date": "2026-03-07", "name": "Machine Girl / Show Me The Body"},
        {"date": "2026-04-17", "name": "Acid Bath / Crowbar / Eyehategod"},
        {"date": "2026-06-13", "name": "The Last Dinner Party"}
    ]
}

def fetch_tm():
    api_key = os.getenv("TM_API_KEY")
    if not api_key: return []
    LAT_LONG = "33.7490,-84.3880"
    RADIUS = "30"
    # Music (KZFzniwnSyZfZ7v7nJ) and Musicals (KnvZfZ7v7n1)
    segment_ids = "KZFzniwnSyZfZ7v7nJ,KnvZfZ7v7n1"
    
    res, seen = [], set()
    for page in range(10): 
        try:
            url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={api_key}&geoPoint={LAT_LONG}&radius={RADIUS}&unit=miles&classificationId={segment_ids}&size=100&page={page}&sort=date,asc"
            r = requests.get(url)
            data = r.json()
            events = data.get('_embedded', {}).get('events', [])
            if not events: break
            for e in events:
                if e['id'] not in seen:
                    v_info = e['_embedded']['venues'][0]
                    if v_info.get('state', {}).get('stateCode') == 'GA':
                        res.append({"id": e['id'], "name": e['name'], "date": e['dates']['start']['localDate'], "venue": v_info['name'], "url": e['url']})
                        seen.add(e['id'])
            time.sleep(0.3) 
        except Exception: break
    return res

def build_web_page():
    db = SessionLocal()
    events = db.query(Event).order_by(Event.date_time).all()
    rows_html = ""
    for e in events:
        clean_name = e.name.replace("/", "-")
        ics = f"BEGIN:VCALENDAR\\nVERSION:2.0\\nBEGIN:VEVENT\\nSUMMARY:{clean_name}\\nDTSTART:{e.date_time.strftime('%Y%m%d')}T200000\\nLOCATION:{e.venue_name}\\nEND:VEVENT\\nEND:VCALENDAR"
        cal_uri = f"data:text/calendar;charset=utf8,{urllib.parse.quote(ics)}"
        rows_html += f'<tr><td class="date-cell">{e.date_time.strftime("%a, %b %d")}</td><td class="lineup-cell">{e.name}</td><td class="venue-cell">{e.venue_name}</td><td><a href="{e.ticket_url}" target="_blank" class="btn-link">Tickets</a><a href="{cal_uri}" download="{clean_name[:10]}.ics" class="btn-cal">📅 Cal</a></td></tr>'
    try:
        if os.path.exists("index.html"):
            with open("index.html", "r", encoding="utf-8") as f: content = f.read()
            if "<tbody>" in content:
                parts = content.split("<tbody>")
                new_content = parts[0] + "<tbody>" + rows_html + "</tbody>" + parts[1].split("</tbody>")[1]
                with open("index.html", "w", encoding="utf-8") as f: f.write(new_content)
    except Exception: pass
    finally: db.close()

def sync():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        tm_shows = fetch_tm()
        db.query(Event).delete()
        today = date.today()
        # Process Ticketmaster
        for e in tm_shows:
            dt = datetime.strptime(e['date'], "%Y-%m-%d").date()
            if dt >= today: db.add(Event(tm_id=e['id'], name=e['name'], date_time=dt, venue_name=e['venue'], ticket_url=e['url']))
        
        # Generic Venue Links
        links = {V529: "https://529atlanta.com/calendar/", EARL: "https://badearl.freshtix.com/https://www.freshtix.com/search?category=&end=&query=the+EARL&start=&state=GA", BOGGS: "https://www.freshtix.com/search?category=&end=&query=Boggs%20Social&start=&state=GA", EASTERN: "https://easternatl.com", T_WEST: "https://terminalwestatl.com", VARIETY: "https://varietyplayhouse.com", CULT_SHOCK: "https://cultureshockatl.com/#/events/"}
        
        # Process Verified Data
        for venue, shows in VERIFIED_DATA.items():
            for s in shows:
                dt = datetime.strptime(s['date'], "%Y-%m-%d").date()
                if dt >= today:
                    # Use specific URL if provided, otherwise fallback to venue generic link
                    t_url = s.get('url', links.get(venue, "#"))
                    db.add(Event(tm_id=f"man-{venue[:3].lower()}-{s['date']}", name=s['name'], date_time=dt, venue_name=venue, ticket_url=t_url))
        
        db.commit()
        build_web_page()
    finally: db.close()

if __name__ == "__main__":
    sync()