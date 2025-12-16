import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Correct absolute imports for local files
from database import init_db, fetch_events 
from collector import fetch_and_save_events

# --- Lifespan Function (Handles Startup/Shutdown) ---
# This runs async functions (init_db, collector) before the server starts accepting requests
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize the database (creates tables)
    print("Database initialization starting...")
    await init_db() 
    print("Database initialization complete.")
    
    # 2. RUN THE COLLECTOR TO POPULATE DATA
    # This runs once on startup to ensure the database is not empty
    print("Running initial data collector...")
    await fetch_and_save_events()
    print("Initial data collection complete.")
    
    yield
    # Code to run on shutdown (if needed)
    pass
    
# Initialize FastAPI app with the lifespan function
app = FastAPI(lifespan=lifespan) 

# --- CORS Configuration (Finalized) ---
# This allows your local Flutter web app and the live site to connect
origins = [
    # General catch-alls for local development
    "*", 
    "http://localhost",
    "http://127.0.0.1",
    
    # CRITICAL: Specific Flutter port to bypass tough browser security
    "http://localhost:55267", 
    "http://127.0.0.1:55267",
    
    # Add your deployed Railway URL if you had another frontend
    "https://atlantashows-production.up.railway.app",
]

# Apply CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoint Definition ---
@app.get("/")
async def read_root():
    return {"message": "Atlanta Shows API is running!"}

@app.get("/events")
async def get_events():
    # This is the function that READS the data from the database
    # It now correctly calls the fetch_events function from database.py
    events_data = await fetch_events() 
    return events_data