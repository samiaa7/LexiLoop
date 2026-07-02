"""
routers/profiles.py — create/list child profiles belonging to the
logged-in parent/teacher. This is the "evolving profile" every other
part of the system (CNN detection, chat agent, exercises) reads from
and writes to.
"""

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.database import child_profiles_collection, users_collection
from app.schemas import ChildProfileCreate, ChildProfileOut

router = APIRouter(prefix="/children", tags=["children"])


@router.post("", response_model=ChildProfileOut)
async def create_child(req: ChildProfileCreate, user: dict = Depends(get_current_user)):
    doc = {
        "name": req.name,
        "age": req.age,
        "reading_level": req.reading_level,
        "parent_id": user["_id"],
        "total_sessions": 0,
        "common_reversals": [],
        "mood_trend": [],
        "profile_summary": "",   # evolving summary the LangChain agent updates
    }
    result = await child_profiles_collection().insert_one(doc)
    await users_collection().update_one(
        {"_id": ObjectId(user["_id"])},
        {"$push": {"child_ids": str(result.inserted_id)}},
    )
    doc["id"] = str(result.inserted_id)
    return ChildProfileOut(**doc)


@router.get("", response_model=list[ChildProfileOut])
async def list_children(user: dict = Depends(get_current_user)):
    cursor = child_profiles_collection().find({"parent_id": user["_id"]})
    children = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        children.append(ChildProfileOut(**doc))
    return children


@router.get("/{child_id}", response_model=ChildProfileOut)
async def get_child(child_id: str, user: dict = Depends(get_current_user)):
    doc = await child_profiles_collection().find_one({"_id": ObjectId(child_id)})
    if not doc or doc["parent_id"] != user["_id"]:
        raise HTTPException(status_code=404, detail="Child profile not found")
    doc["id"] = str(doc["_id"])
    return ChildProfileOut(**doc)
