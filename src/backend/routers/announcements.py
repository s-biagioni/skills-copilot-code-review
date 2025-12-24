"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


class AnnouncementCreate(BaseModel):
    message: str
    start_date: str | None = None
    expiration_date: str
    created_by: str


class AnnouncementUpdate(BaseModel):
    message: str | None = None
    start_date: str | None = None
    expiration_date: str | None = None


@router.get("/active")
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements (within date range)"""
    now = datetime.utcnow().isoformat()
    
    # Query for active announcements
    query = {
        "expiration_date": {"$gte": now}
    }
    
    announcements = list(announcements_collection.find(query))
    
    # Filter by start_date if present
    active_announcements = []
    for announcement in announcements:
        start_date = announcement.get("start_date")
        if start_date is None or start_date <= now:
            # Convert ObjectId to string for JSON serialization
            announcement["_id"] = str(announcement["_id"])
            active_announcements.append(announcement)
    
    # Sort by created_at descending (newest first)
    active_announcements.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return active_announcements


@router.get("/all")
def get_all_announcements(username: str) -> List[Dict[str, Any]]:
    """Get all announcements for management (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Get all announcements
    announcements = list(announcements_collection.find({}))
    
    # Convert ObjectId to string for JSON serialization
    for announcement in announcements:
        announcement["_id"] = str(announcement["_id"])
    
    # Sort by created_at descending (newest first)
    announcements.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return announcements


@router.post("/create")
def create_announcement(announcement: AnnouncementCreate) -> Dict[str, Any]:
    """Create a new announcement (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": announcement.created_by})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Validate dates
    try:
        expiration_datetime = datetime.fromisoformat(announcement.expiration_date.replace('Z', '+00:00'))
        if announcement.start_date:
            start_datetime = datetime.fromisoformat(announcement.start_date.replace('Z', '+00:00'))
            if start_datetime >= expiration_datetime:
                raise HTTPException(status_code=400, detail="Start date must be before expiration date")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Create announcement document
    announcement_doc = {
        "message": announcement.message,
        "start_date": announcement.start_date,
        "expiration_date": announcement.expiration_date,
        "created_by": announcement.created_by,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Insert into database
    result = announcements_collection.insert_one(announcement_doc)
    announcement_doc["_id"] = str(result.inserted_id)
    
    return announcement_doc


@router.put("/update/{announcement_id}")
def update_announcement(announcement_id: str, announcement: AnnouncementUpdate, username: str) -> Dict[str, Any]:
    """Update an existing announcement (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Find existing announcement
    try:
        existing = announcements_collection.find_one({"_id": ObjectId(announcement_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Prepare update document
    update_doc = {}
    if announcement.message is not None:
        update_doc["message"] = announcement.message
    if announcement.start_date is not None:
        update_doc["start_date"] = announcement.start_date
    if announcement.expiration_date is not None:
        update_doc["expiration_date"] = announcement.expiration_date
    
    # Validate dates if both are being set
    if "start_date" in update_doc and "expiration_date" in update_doc:
        try:
            start_datetime = datetime.fromisoformat(update_doc["start_date"].replace('Z', '+00:00'))
            expiration_datetime = datetime.fromisoformat(update_doc["expiration_date"].replace('Z', '+00:00'))
            if start_datetime >= expiration_datetime:
                raise HTTPException(status_code=400, detail="Start date must be before expiration date")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Update announcement
    if update_doc:
        announcements_collection.update_one(
            {"_id": ObjectId(announcement_id)},
            {"$set": update_doc}
        )
    
    # Return updated announcement
    updated = announcements_collection.find_one({"_id": ObjectId(announcement_id)})
    updated["_id"] = str(updated["_id"])
    
    return updated


@router.delete("/delete/{announcement_id}")
def delete_announcement(announcement_id: str, username: str) -> Dict[str, str]:
    """Delete an announcement (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Delete announcement
    try:
        result = announcements_collection.delete_one({"_id": ObjectId(announcement_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
