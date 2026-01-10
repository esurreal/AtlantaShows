import os
import requests
import time
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

raw_db_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL", "sqlite:///shows.db")
db_url = raw_db_url.replace("postgres://", "postgresql://", 1) if "postgres://" in raw_db_url else raw_db_url
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

BOGGS = "Boggs Social & Supply"
EARL = "The EARL"
V529 = "529"
CULT_SHOCK = "Culture Shock"
EASTERN = "The Eastern"
MASQ = "The Masquerade"
T_WEST = "Terminal West"
VARIETY = "Variety Playhouse"

# VERIFIED LIST: Kept exactly as requested
VERIFIED_DATA = {
    V529: [
        {"date": "2026-01-03", "name": "Edwin & My Folks / Rahbi"},
        {"date": "2026-01-08", "name": "Downbeats & Distortions / Lovehex"},
        {"date": "2026-01-09", "name": "The Taj Motel Trio / Analog Day Dream"},
        {"date": "2026-01-10", "name": "Nick Nasty / Close To Midnight"},
        {"date": "2026-01-15", "name": "Elysium / After All This / Winder"},
        {"date": "2026-01-16", "name": "Unfaced Ree / Phamily & Friends"},
        {"date": "2026-01-18", "name": "The Warsaw Clinic / Dirty Holly"},
        {"date": "2026-01-19", "name": "Anti-Sapien / Borzoi / Sewage Bath"},
        {"date": "2026-01-20", "name": "ENMY / Softspoken / Summer Hoop"},
        {"date": "2026-01-22", "name": "SUMPP"},
        {"date": "2026-01-23", "name": "High On Fire / Hot Ram (Night 1)"},
        {"date": "2026-01-24", "name": "High On Fire / Apostle (Night 2)"},
        {"date": "2026-01-29", "name": "Graveyard Hours / Triangle Fire"},
        {"date": "2026-01-30", "name": "Joshua Quimby"},
        {"date": "2026-01-31", "name": "Too Hot for Leather / Yevara"},
        {"date": "2026-02-06", "name": "Parachutes / Tiny Banshee"},
        {"date": "2026-02-13", "name": "Breaux / The Catastrophes"},
        {"date": "2026-02-15", "name": "Hearts Gone South / Sid Jerr-Dan"},
        {"date": "2026-02-24", "name": "A Killer's Confession / Saints of Solomon"},
        {"date": "2026-02-27", "name": "Makes My Blood Dance / The Unknown"},
        {"date": "2026-02-28", "name": "Yosemite In Black / Resistor"},
        {"date": "2026-03-01", "name": "Vicious Rumors / Paladin / Jaeger"},
        {"date": "2026-03-06", "name": "The Pentagram String Band"},
        {"date": "2026-03-08", "name": "Ventana / Aeternum"},
        {"date": "2026-03-13", "name": "Bible Belt Massacre / Vickis Dream"},
        {"date": "2026-03-21", "name": "DONEFOR / Red Hot Empty (Live Loud)"},
        {"date": "2026-04-04", "name": "Lew Sid"},
        {"date": "2026-05-02", "name": "Uada / Mortiis / Rome"}
    ],
    EARL: [
        {"date": "2026-01-09", "name": "Numbers Station Records Showcase"},
        {"date": "2026-01-10", "name": "Gringo Star / The Sporrs"},
        {"date": "2026-01-11", "name": "The Last Revel"},
        {"date": "2026-01-15", "name": "Rod Hamdallah / Chester Leathers"},
        {"date": "2026-01-16", "name": "Pissed Jeans / Morgan Garrett"},
        {"date": "2026-01-17", "name": "Country Westerns / Ultra Lights"},
        {"date": "2026-01-19", "name": "Modern Nature / Brigid Dawson"},
        {"date": "2026-01-20", "name": "Friendship / Little Mazarn"},
        {"date": "2026-01-21", "name": "Shiner / Dropsonic / Bursting"},
        {"date": "2026-01-22", "name": "Off With Their Heads / Smug LLC"},
        {"date": "2026-01-23", "name": "Sean Rowe / Slow Parade"},
        {"date": "2026-01-24", "name": "Vio-lence / Deceased / Nunslaughter"},
        {"date": "2026-01-25", "name": "Low Water Bridge Band"},
        {"date": "2026-01-30", "name": "God Bullies / Vincas / Rubber Udder"},
        {"date": "2026-01-31", "name": "K Michelle Dubois / Gouwzee"},
        {"date": "2026-02-05", "name": "Taper's Choice / Rich Ruth"},
        {"date": "2026-02-06", "name": "Matt Pryor / Small Uncle"},
        {"date": "2026-02-07", "name": "Bad Bad Hats / Smut"},
        {"date": "2026-02-11", "name": "Venus & The Flytraps"},
        {"date": "2026-02-12", "name": "Robin Shakedown (El Refugio Benefit)"},
        {"date": "2026-02-13", "name": "James Hall & The Steady Wicked"},
        {"date": "2026-02-20", "name": "True Blossom / Sleepers Club"},
        {"date": "2026-02-21", "name": "Nuovo Testamento / Dark Chisme"},
        {"date": "2026-02-22", "name": "Jake Xerxes Fussell / Dougie Poole"},
        {"date": "2026-02-24", "name": "Spiritual Cramp / Liberty and Justice"},
        {"date": "2026-02-26", "name": "Dyskrasia / Normal Bias"},
        {"date": "2026-02-27", "name": "The Constellations / Anthmz"},
        {"date": "2026-02-28", "name": "Prison Affair / RMBLR"},
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
        {"date": "2026-01-10", "name": "Big Mike Geier's Elvis Royale (Night 1)"},
        {"date": "2026-01-11", "name": "Big Mike Geier's Elvis Royale (Night 2)"},
        {"date": "2026-01-16", "name": "Magic City Hippies / Supertaste"},
        {"date": "2026-01-17", "name": "Spafford / Frute"},
        {"date": "2026-01-23", "name": "Leo Kottke"},
        {"date": "2026-01-24", "name": "The Sundogs (Tom Petty Tribute)"},
        {"date": "2026-01-29", "name": "Goldford / Madeline Edwards"},
        {"date": "2026-01-30", "name": "Nacho Redondo"},
        {"date": "2026-02-03", "name": "James McMurtry / Bettysoo"},
        {"date": "2026-02-05", "name": "Don Was & The Pan-Detroit Ensemble"},
        {"date": "2026-02-06", "name": "Dry Cleaning (Cancelled)"},
        {"date": "2026-02-07", "name": "The Movement / Tropidelic"},
        {"date": "2026-02-13", "name": "Smithsonian & The Remakes (Night 1)"},
        {"date": "2026-02-14", "name": "Smithsonian & The Remakes (Night 2)"},
        {"date": "2026-02-15", "name": "Rory Scovel"},
        {"date": "2026-02-20", "name": "Peter McPoland / Dug"},
        {"date": "2026-02-21", "name": "Marty Stuart / Hogslop String Band"},
        {"date": "2026-02-27", "name": "Big Head Todd and The Monsters"},
        {"date": "2026-02-28", "name": "Billy F. Gibbons & The BFG Band"},
        {"date": "2026-03-03", "name": "Evan Honer / Harf."},
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
        {"date": "2026-01-09", "name": "ozello / Kyle Lewis"},
        {"date": "2026-01-10", "name": "Elijah Cruise / MENU"},
        {"date": "2026-01-17", "name": "The Carolyn / Knives"},
        {"date": "2026-01-23", "name": "Empty Parking Lot / Lqm"},
        {"date": "2026-01-31", "name": "Palaces / Muelas"},
        {"date": "2026-02-05", "name": "Ritual Arcana (Wino)"},
        {"date": "2026-02-06", "name": "Atoll / Truckstop Dickpill"},
        {"date": "2026-02-07", "name": "Temple of Love / Black Fractal"},
        {"date": "2026-03-03", "name": "Temptress / Friendship Commanders"},
        {"date": "2026-03-06", "name": "Author & Punisher / King Yosef"}
    ],
    CULT_SHOCK: [
        {"date": "2026-01-18", "name": "Second Death / Cruel Bones"},
        {"date": "2026-01-31", "name": "Los Ojos Muertos"},
        {"date": "2026-02-20", "name": "SinThya / Endeavor Into the Dark"},
        {"date": "2026-03-14", "name": "SinThya (Return Show)"},
        {"date": "2026-03-20", "name": "Bullshit Detector / Antagonizers"}
    ],
    EASTERN: [
        {"date": "2026-01-23", "name": "Ravenscoon / Artifakts"},
        {"date": "2026-01-24", "name": "Ravenscoon / Know Good"},
        {"date": "2026-01-29", "name": "The Wood Brothers / Ric Robertson"},
        {"date": "2026-02-06", "name": "Elevation Rhythm"},
        {"date": "2026-02-07", "name": "RnB at 9am"},
        {"date": "2026-02-13", "name": "Inzo / Truth"},
        {"date": "2026-02-14", "name": "Joe Russo's Almost Dead"},
        {"date": "2026-02-19", "name": "Niko Moon"},
        {"date": "2026-02-20", "name": "Alleycvt / Steller"},
        {"date": "2026-02-25", "name": "Jesse Welles / S.G. Goodman"},
        {"date": "2026-02-27", "name": "STS9 w/ Lotus (Night 1)"},
        {"date": "2026-02-28", "name": "STS9 w/ Lotus (Night 2)"},
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
    ],
    T_WEST: [
        {"date": "2026-01-13", "name": "Indigo Girls (Sold Out)"},
        {"date": "2026-01-16", "name": "Ruston Kelly / Verygently"},
        {"date": "2026-01-17", "name": "Shlump / Stylust"},
        {"date": "2026-01-22", "name": "54 Ultra / Orca"},
        {"date": "2026-01-23", "name": "Stop Light Observations"},
        {"date": "2026-01-24", "name": "Bayker Blankenship"},
        {"date": "2026-01-29", "name": "Redferrin / Shaylen"},
        {"date": "2026-01-30", "name": "Tinzo + Jojo / Raecola"},
        {"date": "2026-01-31", "name": "Eddie 9V / Nether Hour"},
        {"date": "2026-02-01", "name": "Couch / Thumber"},
        {"date": "2026-02-02", "name": "Drama / Blank Sense"},
        {"date": "2026-02-19", "name": "clipping. / Open Mike Eagle"},
        {"date": "2026-05-14", "name": "Drug Church / White Reaper"}
    ],
    MASQ: [
        {"date": "2026-02-19", "name": "clipping. / Open Mike Eagle (Heaven)"}
    ]
}

def fetch_ticketmaster():
    api_key = os.getenv("TM_API_KEY")
    if not api_key: return []
    
    venue_ids = [
        "KovZpZAJ67eA", "KovZpZAJ67lA", "KovZpZAJ671A", # Masquerade Rooms
        "KovZpZAFF1tA", "KovZpZAEA71A", "KovZpZAEA7vA", # Center Stage / Loft / Vinyl
        "KovZpZAEk7IA", "KovZpZAE6eEA", "KovZpZAEkAaA", # Buckhead / Roxy / Chastain
        "KovZpZAFFdlA", "KovZpZAEk6vA"                 # Ameris / Lakewood
    ]
    results = []
    
    for v_id in venue_ids:
        # Increased size to 100 to make sure we don't miss music dates
        url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={api_key}&venueId={v_id}&classificationName=music&size=100"
        try:
            r = requests.get(url)
            data = r.json()
            events = data.get('_embedded', {}).get('events', [])
            for e in events:
                results.append({
                    "id": e['id'], "name": e['name'], "date": e['dates']['start']['localDate'],
                    "venue": e['_embedded']['venues'][0]['name'], "url": e['url']
                })
            time.sleep(0.3) 
        except: continue
    return results

def clean_and_sync():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("[*] Rebuilding Master Database...")
        tm_list = fetch_ticketmaster()
        db.query(Event).delete()
        today = date.today()

        for e in tm_list:
            event_date = datetime.strptime(e['date'], "%Y-%m-%d").date()
            if event_date < today: continue
            
            # Safeguard expanded to prevent double-counting if TM lists manual venues
            manual_venues = ["529", "boggs", "the earl", "culture shock", "the eastern", "terminal west", "variety playhouse"]
            if any(v.lower() in e['venue'].lower() for v in manual_venues):
                continue
            
            db.add(Event(tm_id=e['id'], name=e['name'], date_time=event_date, venue_name=e['venue'], ticket_url=e['url']))
        
        for venue, shows in VERIFIED_DATA.items():
            link = "https://www.freshtix.com"
            if venue == V529: link = "https://529atlanta.com/calendar/"
            if venue == EARL: link = "https://badearl.freshtix.com/"
            if venue == BOGGS: link = "https://www.freshtix.com/organizations/arippinproduction"
            if venue == CULT_SHOCK: link = "https://www.venuepilot.co/events/cultureshock"
            if venue == EASTERN: link = "https://www.easternatl.com/calendar/"
            if venue == T_WEST: link = "https://www.terminalwestatl.com/calendar/"
            if venue == VARIETY: link = "https://www.varietyplayhouse.com/calendar/"
            if venue == MASQ: link = "https://www.masqueradeatlanta.com/events/"
            
            for item in shows:
                dt = datetime.strptime(item['date'], "%Y-%m-%d").date()
                if dt < today: continue
                db.add(Event(
                    tm_id=f"man-{venue[:3].lower()}-{item['date']}-{item['name'][:5].lower().replace(' ', '')}",
                    name=item['name'], date_time=dt, venue_name=venue, ticket_url=link
                ))
        db.commit()
        print(f"[+] Sync complete! Added {db.query(Event).count()} total events.")
    finally:
        db.close()

if __name__ == "__main__":
    clean_and_sync()