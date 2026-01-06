import os
import subprocess
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

def run_collector():
    # This runs the scraper in a separate system process
    subprocess.Popen(["python", "collector.py"])

@app.on_event("startup")
async def startup_event():
    # Trigger the scraper 5 seconds after the server starts
    run_collector()

@app.get("/")
def read_root():
    return {"status": "Server is up", "msg": "Scraper is running in background"}