"""
API router for the AI Assistant / Gemini Reviews Chat.
"""

import os
import json
import uuid
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.job_store import job_store
from app.schemas import APIResponse
from app.scrapers.google_maps import GoogleMapsScraper
from app.routers.scrape import _run_scraper_task

logger = logging.getLogger(__name__)
router = APIRouter()

# Directory for persisting chat session context (history & reviews)
AI_SESSIONS_DIR = os.path.join(settings.EXPORT_DIR, "ai_sessions")
os.makedirs(AI_SESSIONS_DIR, exist_ok=True)

class AIChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    max_reviews: Optional[int] = 100

class AIChatResponse(BaseModel):
    reply: str
    session_id: str
    scraped_place: Optional[Dict[str, Any]] = None
    job_id: Optional[str] = None

# Helper to load GenAI SDK safely
def get_gemini_client():
    try:
        from google import genai
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="The Google GenAI Python SDK is not installed or loading. Please wait a moment and try again."
        )
    
    api_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="GEMINI_API_KEY is not set in the environment variables. Please add it to your .env file."
        )
    
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize Google GenAI Client: {str(e)}"
        )

# Helper to load and save session data
def load_session(session_id: str) -> dict:
    file_path = os.path.join(AI_SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
    return {"history": [], "reviews": [], "scraped_place": None}

def save_session(session_id: str, data: dict):
    file_path = os.path.join(AI_SESSIONS_DIR, f"{session_id}.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving session {session_id}: {e}")

@router.post("/chat", response_model=AIChatResponse, summary="Send a message to the Reviews Assistant")
async def chat_endpoint(request: AIChatRequest):
    client = get_gemini_client()
    from google.genai import types
    
    session_id = request.session_id or str(uuid.uuid4())
    session_data = load_session(session_id)
    
    # ── Step 1: Detect Scrape Intent ──────────────────────────────────────────
    # We ask Gemini to analyze if the user is asking to scrape reviews for a location.
    intent_prompt = (
        "Analyze the user's message. Does the user want to scrape, extract, collect, find or search "
        "Google Maps reviews of a specific location/business/place? Or did they just name a place to scrape?\n"
        "Reply ONLY with a raw JSON object containing these keys:\n"
        "- \"is_scrape_request\": boolean (true if they want to run a scraper for a business, false if they are asking questions or chatting)\n"
        "- \"location\": string (the name of the business/place they want to scrape, or null if not a scrape request)\n"
        "- \"max_reviews\": integer (the number of reviews they requested to scrape, or 100 as default)\n\n"
        f"User message: \"{request.message}\""
    )
    
    try:
        intent_response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=intent_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        intent = json.loads(intent_response.text)
    except Exception as e:
        logger.error(f"Failed to detect intent: {e}")
        intent = {"is_scrape_request": False, "location": None, "max_reviews": 100}
        
    is_scrape = intent.get("is_scrape_request", False)
    location = intent.get("location")
    
    # ── Step 2: Handle Scraping Job ──────────────────────────────────────────
    if is_scrape and location:
        max_reviews = intent.get("max_reviews") or request.max_reviews or 100
        logger.info(f"AI Assistant triggered scraping job for: '{location}' with max_reviews={max_reviews}")
        
        # 1. Create the job in the database/job_store
        job = job_store.create("google_maps", location, {"max_reviews": max_reviews})
        job_id = job["id"]
        
        # 2. Execute the scraper synchronously (within our async handler context)
        # This will update job_store with status, progress, logs, and results.
        await _run_scraper_task(job_id, GoogleMapsScraper, location, {"max_reviews": max_reviews})
        
        # 3. Retrieve results
        result = job_store.get_result(job_id)
        job_status = job_store.get(job_id) or {}
        
        if not result or job_status.get("status") == "failed":
            error_msg = job_status.get("error_message") or "Unknown scraper failure."
            reply = f"I started a scraper job for '{location}' (Job ID: {job_id}), but the job failed. Error: {error_msg}"
            
            # Record failed interaction in history
            session_data["history"].append({"role": "user", "text": request.message})
            session_data["history"].append({"role": "model", "text": reply})
            save_session(session_id, session_data)
            
            return AIChatResponse(
                reply=reply,
                session_id=session_id,
                job_id=job_id
            )
            
        # 4. Save place details and reviews to the session file
        session_data["scraped_place"] = {
            "name": result.get("name", location),
            "category": result.get("category", ""),
            "rating": result.get("rating"),
            "total_reviews": result.get("total_reviews", 0),
            "address": result.get("address", ""),
            "phone": result.get("phone", ""),
            "website": result.get("website", ""),
            "maps_url": result.get("maps_url", "")
        }
        session_data["reviews"] = result.get("reviews", [])
        
        # 5. Generate confirmation message using Gemini
        confirm_prompt = (
            f"The scraper successfully extracted {len(session_data['reviews'])} reviews for the business "
            f"'{session_data['scraped_place']['name']}' (average rating: {session_data['scraped_place']['rating']}). "
            "Write a friendly, professional response informing the user that the scraping is complete, "
            "summarizing the rating and the number of reviews found, and letting them know they can now ask questions about these reviews."
        )
        
        try:
            confirm_response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=confirm_prompt
            )
            reply = confirm_response.text.strip()
        except Exception:
            reply = (
                f"I found {len(session_data['reviews'])} reviews for {session_data['scraped_place']['name']} "
                f"with an average rating of {session_data['scraped_place']['rating']}. The scraping is complete. "
                "You can now ask questions about these reviews."
            )
            
        # Record success interaction
        session_data["history"].append({"role": "user", "text": request.message})
        session_data["history"].append({"role": "model", "text": reply})
        save_session(session_id, session_data)
        
        return AIChatResponse(
            reply=reply,
            session_id=session_id,
            scraped_place=session_data["scraped_place"],
            job_id=job_id
        )
        
    # ── Step 3: Handle Regular Q&A ───────────────────────────────────────────
    # If the user has already loaded reviews in this session, feed them into context
    system_instruction = ""
    if session_data.get("reviews"):
        place = session_data["scraped_place"] or {}
        reviews_summary = []
        # Feed up to 150 reviews to fit comfortably in context
        for r in session_data["reviews"][:150]:
            reviews_summary.append(
                f"- Rating: {r.get('rating')} stars | Date: {r.get('review_date')} | Author: {r.get('reviewer_name')}\n"
                f"  Text: {r.get('text')}"
            )
        
        reviews_text = "\n\n".join(reviews_summary)
        
        system_instruction = (
            "You are a professional Reviews Analysis Assistant for the Scrappers Dashboard.\n"
            f"The user has scraped reviews for '{place.get('name')}' on Google Maps.\n"
            f"Business info:\n"
            f"- Category: {place.get('category')}\n"
            f"- Rating: {place.get('rating')} stars\n"
            f"- Total reviews on Google: {place.get('total_reviews')}\n"
            f"- Address: {place.get('address')}\n"
            f"- Website: {place.get('website')}\n\n"
            f"Here are the scraped reviews:\n"
            f"{reviews_text}\n\n"
            "Analyze these reviews to answer the user's questions. Identify themes, pros and cons, customer service issues, "
            "product quality, or delivery speed. Be extremely objective. Reference comments without fabricating details."
        )
    else:
        system_instruction = (
            "You are a helpful Reviews Scrape & Chat Assistant. The user has not scraped any reviews yet.\n"
            "To scrape reviews of a business on Google Maps, tell the user to enter the location name or search query, "
            "e.g., 'extract reviews of Sofa Gold Mall' or 'Sofa Gold Mall'."
        )
        
    # Build history objects
    history_objects = []
    for msg in session_data["history"]:
        history_objects.append(
            types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["text"])]
            )
        )
        
    try:
        chat = client.chats.create(
            model="gemini-2.5-flash",
            history=history_objects,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        response_obj = chat.send_message(request.message)
        reply = response_obj.text.strip()
    except Exception as e:
        logger.error(f"Chat completion failed: {e}")
        reply = f"Error generating response: {str(e)}"
        
    # Save the updated history
    session_data["history"].append({"role": "user", "text": request.message})
    session_data["history"].append({"role": "model", "text": reply})
    save_session(session_id, session_data)
    
    return AIChatResponse(
        reply=reply,
        session_id=session_id,
        scraped_place=session_data.get("scraped_place")
    )
