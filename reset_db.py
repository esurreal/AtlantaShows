import os
from sqlalchemy import create_engine, text

# Get the URL from your environment (or paste your public URL here)
db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("Error: DATABASE_URL not found. Run this with your public URL set!")
else:
    # Ensure the URL is compatible with SQLAlchemy
    if "postgres://" in db_url:
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(db_url)
    
    print("Connecting to Railway to wipe the 'events' table...")
    try:
        with engine.connect() as conn:
            # This deletes all rows but keeps the table structure
            conn.execute(text("DELETE FROM events;"))
            conn.commit()
            print("Successfully wiped all shows from the database.")
    except Exception as e:
        print(f"Error: {e}")