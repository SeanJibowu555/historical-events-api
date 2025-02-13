from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
from .database import events_collection, client
from dotenv import load_dotenv
import requests
from app.utils.openai_client import generate_summary
from app.utils.openai_client import client

load_dotenv()

app = FastAPI()

# Define the response model
class HistoricalEventResponse(BaseModel):
    id: str
    date: str
    access_timestamp: str
    location: str
    theme: str
    summary: str          # From Wikipedia
    ai_summary: str       # GPT-generated with citations
    sources: List[dict]   # Now includes OpenAI source
    people: List[dict]

    class Config:
        from_attributes = True

# Fetch Wikipedia events for a given year
def fetch_wikipedia_events(year: str):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{year}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

# Startup event to check MongoDB connection
@app.on_event("startup")
async def startup_db_client():
    try:
        client.admin.command('ping')
        print("✅ MongoDB connected")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")

# Get all events with optional filters
@app.get("/events/", response_model=List[HistoricalEventResponse])
def get_events(
    date: Optional[str] = None,
    location: Optional[str] = None,
    theme: Optional[str] = None
):
    query = {}
    if date:
        query["date"] = {"$regex": date, "$options": "i"}
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    if theme:
        query["theme"] = {"$regex": theme, "$options": "i"}
    
    events = list(events_collection.find(query))
    return [{"id": str(event["_id"]), **event} for event in events]

# Get a specific event by ID
@app.get("/events/{event_id}", response_model=HistoricalEventResponse)
def get_event(event_id: str):
    try:
        object_id = ObjectId(event_id)
        event = events_collection.find_one({"_id": object_id})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return {"id": str(event["_id"]), **event}
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")

# Fetch and store events for a given year
@app.post("/events/fetch/{year}")
def fetch_and_store_events(year: str):
    data = fetch_wikipedia_events(year)
    if not data:
        raise HTTPException(status_code=404, detail="Year not found")
    
    try:
        # Generate AI summary using Wikipedia's extract
        ai_summary = generate_summary(data.get("extract", ""))  # Pass the Wikipedia extract
        
        event = {
            "date": year,  # Use the year parameter as the event date
            "access_timestamp": data.get("timestamp", "Unknown date"),
            "location": "Global",
            "theme": "General",
            "summary": data.get("extract", "No summary available"),
            "ai_summary": ai_summary,
            "sources": [
                {
                    "type": "Wikipedia",
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", "")
                },
                {
                    "type": "AI Generation",
                    "model": "GPT-4o",  # Ensure this matches your actual model
                    "provider": "OpenAI",
                    "citation_note": "Citations [1], [2] refer to Wikipedia sources",
                    "disclaimer": "AI content should be verified with primary sources"
                }
            ],
            "people": []
        }
        result = events_collection.insert_one(event)
        return {"message": "Event stored", "id": str(result.inserted_id)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)