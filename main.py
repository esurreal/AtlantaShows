from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import uvicorn
# Assuming these modules are in your root directory (or imported correctly)
#from database import fetch_events 
#from database import fetch_eventbrite_by_location, normalize_eventbrite 
# Removed unnecessary flask/flask_cors imports

# --- FastAPI Initialization ---
app = FastAPI()

# 🛑 1. CORS Middleware Setup (Fixes XMLHttpRequest error) 🛑
# Allows requests from any origin (*) during development
origins = ["*",
    "http://127.0.0.1:50345", # <-- ADD THIS SPECIFIC DEBUGGER HOST/PORT
    "http://localhost:50345", # <-- ADD THIS LOCALHOST VARIANT
    "http://127.0.0.1:9100",
    ] 

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ------------------------------

# --- 2. Database Setup ---
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Get the DATABASE_URL from environment variables
db_url = os.getenv("DATABASE_URL")

if not db_url:
    # This will cause a fast crash if the environment variable is missing
    raise RuntimeError(
        "DATABASE_URL environment variable not set. "
        "Please set it in Railway project variables."
    )

# Convert to async format for SQLAlchemy (assuming it's needed for other parts)
async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

# Create the async engine
engine = create_async_engine(async_db_url, future=True)

# Create a session factory for async sessions
AsyncSessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

# Example usage function (Kept for consistency, though fetch_events is self-contained)
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

print("Database engine initialized successfully")

# --- 3. API Endpoints ---

@app.get("/events")
async def get_events():
    # 🛑 CRITICAL FIX: Ensure fetch_events is awaited 🛑
    # It must be awaited since it's an async function (async def fetch_events)
    events_data = await fetch_events() 
    
    # Ensure a clean list is returned if no data is found (for Flutter compatibility)
    if not events_data:
        return []
        
    return events_data

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

# --- 4. Uvicorn Execution Block ---
# Note: Since your Railway command is 'uvicorn main:app ...', this block is less critical,
# but it's good practice for local development.

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000)) 
    
    # 🛑 NOTE: The Uvicorn string here is 'main:app' because this file is in the root. 
    # This is also what your successful Railway command should now be pointing to.
    uvicorn.run("main:app", host="0.0.0.0", port=port)