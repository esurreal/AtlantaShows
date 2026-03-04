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

# Venue Constants for Verified Data
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
        {"date": "2026-03-06", "name": "The Pentagram String Band"},
        {"date": "2026-03-08", "name": "Ventana / Aeternum"},
        {"date": "2026-03-13", "name": "Bible Belt Massacre / Vickis Dream"},
        {"date": "2026-03-21", "name": "DONEFOR / Red Hot Empty (Live Loud)"},
        {"date": "2026-04-04", "name": "Lew Sid"},
        {"date": "2026-05-02", "name": "Uada / Mortiis / Rome"}
    ],
    EARL: [
        {"date": "2026-03-04", "name": "The Deslondes / Sabine McCalla"},
        {"date": "2026-03-05", "name": "Daiseychain / Reverends"},
        {"date": "2026-03-12", "name": "Twen / Monsoon"},
        {"date": "2026-03-16", "name": "Westerman / Otto Benson"},
        {"date": "2026-03-17", "name": "Skullcrusher"},
        {"date": "2026-03-18", "name": "Cornelia Murr"},
        {"date": "2026-03-21", "name": "Vessel (Album Release) / Malevich"},
        {"date": "2026-03-26", "name": "Orcutt, Shelley, Miller / Chris Forsyth"},
        {"date": "2026-03-27", "name": "Hudson Freeman"},
        {"date": "2026-03-28", "name": "Courtney Marie Andrews / Taylor Zachry"},
        {"date": "2026-04-02", "name": "The Wedding Present (Seamonsters 35th)"},
        {"date": "2026-04-10", "name": "Redd Kross"},
        {"date": "2026-04-11", "name": "Field Medic / Euphoria Again"},
        {"date": "2026-04-16", "name": "The Belair Lip Bombs / Dust"},
        {"date": "2026-04-17", "name": "Couch Dog / The Normas"},
        {"date": "2026-04-18", "name": "The Thing / Heffner"},
        {"date": "2026-04-30", "name": "Liz Cooper"},
        {"date": "2026-05-04", "name": "Flyte (Rescheduled)"}
    ],
    VARIETY: [
        {"date": "2026-03-07", "name": "SunSquabi + Manic Focus"},
        {"date": "2026-03-10", "name": "Jordan Jensen"},
        {"date": "2026-03-13", "name": "Drivin' N' Cryin'"},
        {"date": "2026-03-14", "name": "Wednesday / Gouge Away (Sold Out)"},
        {"date": "2026-03-20", "name": "Yacht Rock Revue (Stop Making Sense)"},
        {"date": "2026-03-21", "name": "Mike Gordon"},
        {"date": "2026-03-25", "name": "Richard Thompson"},
        {"date": "2026-03-26", "name": "Cymande"},
        {"date": "2026-03-27", "name": "Madison Cunningham / Annika Bennett"},
        {"date": "2026-03-28", "name": "The Brook & The Bluff"},
        {"date": "2026-03-29", "name": "On Cinema - Live!"},
        {"date": "2026-04-03", "name": "Indigo De Souza"},
        {"date": "2026-04-12", "name": "The Growlers"},
        {"date": "2026-04-14", "name": "Allie X"},
        {"date": "2026-04-16", "name": "Taj Mahal & The Phantom Blues Band"},
        {"date": "2026-04-17", "name": "Leonid & Friends"},
        {"date": "2026-04-18", "name": "Alice Phoebe Lou / John Andrews"},
        {"date": "2026-04-19", "name": "VNV Nation"},
        {"date": "2026-04-21", "name": "Lambrini Girls"},
        {"date": "2026-04-23", "name": "CupcakKe"},
        {"date": "2026-05-06", "name": "Ty Segall"},
        {"date": "2026-05-11", "name": "Thornhill / 156/Silence"},
        {"date": "2026-05-18", "name": "Andrés Cepeda"},
        {"date": "2026-05-19", "name": "The New Pornographers / Will Sheff"},
        {"date": "2026-08-04", "name": "Chance Peña"},
        {"date": "2026-10-09", "name": "Pattie Gonia: Save Her!"},
        {"date": "2026-10-22", "name": "Benjamin Tod & The Inline Six"}
    ],
    BOGGS: [
        {"date": "2026-03-03", "name": "Temptress / Friendship Commanders"},
        {"date": "2026-03-06", "name": "Author & Punisher / King Yosef"},
        {"date": "2026-03-07", "name": "HAMMERHEAD FEST XIV"},
        {"date": "2026-03-08", "name": "Palaces / Muelas / Leafblower"},
        {"date": "2026-03-10", "name": "Over Anna / Kat and the Hurricane"},
        {"date": "2026-03-12", "name": "PAPRIKA / Killian / favvors"},
        {"date": "2026-03-13", "name": "Boys From The County Hell"},
        {"date": "2026-03-21", "name": "Sputnik! Alternative Music Video Night"},
        {"date": "2026-03-27", "name": "Cash Honey / Wardrobe Malfunction"},
        {"date": "2026-03-28", "name": "Void / Phantom / Herakleion"},
        {"date": "2026-04-03", "name": "MENU / Cascadent / Novumora"},
        {"date": "2026-04-05", "name": "Cut Throat Freak Show"},
        {"date": "2026-04-10", "name": "Gooseberry / Recess Party"},
        {"date": "2026-05-02", "name": "RAVEN w/ Special Guests Slackjaw"},
        {"date": "2026-05-20", "name": "Confessions of a Traitor"},
        {"date": "2026-05-23", "name": "Atlanta Ska Night Volume 8!"},
        {"date": "2026-05-26", "name": "OXYGEN DESTROYER"},
        {"date": "2026-06-04", "name": "Conjurer / Sadness / Snooze"}
    ],
    CULT_SHOCK: [
        {"date": "2026-03-07", "name": "Bazooka Tooth (3:00 PM)"},
        {"date": "2026-03-07", "name": "Weekend Evidence (7:00 PM)"},
        {"date": "2026-03-12", "name": "Direct Measure"},
        {"date": "2026-03-14", "name": "SinThya"},
        {"date": "2026-03-16", "name": "Weeping"},
        {"date": "2026-03-18", "name": "SWAG IS BACK TOUR"},
        {"date": "2026-03-20", "name": "Bullshit Detector / Antagonizers"},
        {"date": "2026-03-28", "name": "Vile Mind / Power of Fear"},
        {"date": "2026-04-23", "name": "Sneaky Miles"},
        {"date": "2026-05-19", "name": "Paisley Fields"}
    ],
    EASTERN: [
        {"date": "2026-03-04", "name": "Rich Brian"},
        {"date": "2026-03-06", "name": "Trombone Shorty / New Breed Brass"},
        {"date": "2026-03-07", "name": "Machine Girl / Show Me The Body"},
        {"date": "2026-03-08", "name": "Pink Martini"},
        {"date": "2026-03-12", "name": "Cat Power"},
        {"date": "2026-03-13", "name": "Levity Presents Lasership (Night 1)"},
        {"date": "2026-03-14", "name": "Levity Presents Lasership (Night 2)"},
        {"date": "2026-03-17", "name": "Rainbow Kitten Surprise (Night 1)"},
        {"date": "2026-03-18", "name": "Rainbow Kitten Surprise (Night 2)"},
        {"date": "2026-03-21", "name": "Level Up x Zingara"},
        {"date": "2026-04-03", "name": "William Black"},
        {"date": "2026-04-04", "name": "The Format / Ben Kweller"},
        {"date": "2026-04-08", "name": "Snarky Puppy"},
        {"date": "2026-04-16", "name": "Charles Wesley Godwin"},
        {"date": "2026-04-17", "name": "Acid Bath / Crowbar / Eyehategod"},
        {"date": "2026-04-18", "name": "The Midnight: Time Machines"},
        {"date": "2026-04-24", "name": "Panchiko / Rehash"},
        {"date": "2026-05-08", "name": "St. Paul & The Broken Bones"},
        {"date": "2026-05-09", "name": "moe."},
        {"date": "2026-05-13", "name": "Mac DeMarco (Sold Out)"},
        {"date": "2026-06-13", "name": "The Last Dinner Party"}
    ]
}

def fetch_tm():
    api_key = os.getenv("TM_API_KEY")
    if not api_key: return []
    LAT_LONG = "33.7490,-84.3880"
    RADIUS = "30"
    segment_ids = "KZFzniwnSyZfZ7v7nJ,KnvZfZ7v7n1"
    res, seen = [], set()
    for page in range(10): 
        try:
            url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={api_key}&geoPoint={LAT_LONG}&radius={RADIUS}&unit=miles&classificationId={segment_ids}&size=100&page={page}&sort=date,asc"
            r = requests.get(url)
            data = r.json()
            events = data.get('_embedded', {}).get('events', [])
            if not events:
                break
            for e in events:
                if e['id'] not in seen:
                    v_info = e['_embedded']['venues'][0]
                    if v_info.get('state', {}).get('stateCode') == 'GA':
                        res.append({
                            "id": e['id'], 
                            "name": e['name'], 
                            "date": e['dates']['start']['localDate'], 
                            "venue": v_info['name'], 
                            "url": e['url']
                        })
                        seen.add(e['id'])
            time.sleep(0.3) 
        except Exception as err:
            print(f"Error filtering Ticketmaster: {err}")
            break
    return res

def build_web_page():
    db = SessionLocal()
    events = db.query(Event).order_by(Event.date_time).all()
    rows_html = ""
    for e in events:
        clean_name = e.name.replace("/", "-")
        ics = f"BEGIN:VCALENDAR\\nVERSION:2.0\\nBEGIN:VEVENT\\nSUMMARY:{clean_name}\\nDTSTART:{e.date_time.strftime('%Y%m%d')}T200000\\nLOCATION:{e.venue_name}\\nEND:VEVENT\\nEND:VCALENDAR"
        cal_uri = f"data:text/calendar;charset=utf8,{urllib.parse.quote(ics)}"
        rows_html += f"""
        <tr>
            <td class="date-cell">{e.date_time.strftime("%a, %b %d")}</td>
            <td class="lineup-cell">{e.name}</td>
            <td class="venue-cell">{e.venue_name}</td>
            <td>
                <a href="{e.ticket_url}" target="_blank" class="btn-link">Tickets</a>
                <a href="{cal_uri}" download="{clean_name[:10]}.ics" class="btn-cal">📅 Cal</a>
            </td>
        </tr>"""
    try:
        if os.path.exists("index.html"):
            with open("index.html", "r", encoding="utf-8") as f:
                full_content = f.read()
            if "<tbody>" in full_content and "</tbody>" in full_content:
                parts = full_content.split("<tbody>")
                end_part = parts[1].split("</tbody>")
                new_content = parts[0] + "<tbody>" + rows_html + "</tbody>" + end_part[1]
                with open("index.html", "w", encoding="utf-8") as f:
                    f.write(new_content)
                print("[+] Site updated.")
    except Exception as ex:
        print(f"[!] Build error: {ex}")
    finally:
        db.close()

def sync():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        tm_shows = fetch_tm()
        db.query(Event).delete()
        today = date.today()
        for e in tm_shows:
            dt = datetime.strptime(e['date'], "%Y-%m-%d").date()
            if dt >= today:
                db.add(Event(tm_id=e['id'], name=e['name'], date_time=dt, venue_name=e['venue'], ticket_url=e['url']))
        
        links = {V529: "https://529atlanta.com/calendar/", EARL: "https://badearl.freshtix.com/", BOGGS: "https://freshtix.com", CULT_SHOCK: "https://venuepilot.co", EASTERN: "https://easternatl.com", T_WEST: "https://terminalwestatl.com", VARIETY: "https://varietyplayhouse.com", MASQ: "https://masqueradeatlanta.com"}
        
        for venue, shows in VERIFIED_DATA.items():
            for s in shows:
                dt = datetime.strptime(s['date'], "%Y-%m-%d").date()
                if dt >= today:
                    # UPDATED ID LOGIC: venue + date + band snippet to prevent matinee collisions
                    band_id = s['name'][:5].lower().replace(" ", "")
                    db.add(Event(tm_id=f"man-{venue[:3].lower()}-{s['date']}-{band_id}", name=s['name'], date_time=dt, venue_name=venue, ticket_url=links.get(venue, "#")))
        
        db.commit()
        build_web_page()
    finally: 
        db.close()

if __name__ == "__main__":
    sync()