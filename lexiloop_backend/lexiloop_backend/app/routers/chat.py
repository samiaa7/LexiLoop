"""
routers/chat.py — endpoint the React chatbot UI calls. Delegates to the
LangChain tool-calling agent in ai/agent/agent.py.
"""

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.database import child_profiles_collection
from app.schemas import ChatRequest, ChatResponse
from app.ai.agent.agent import run_agent

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    child = await child_profiles_collection().find_one({"_id": ObjectId(req.child_id)})
    if not child or child["parent_id"] != user["_id"]:
        raise HTTPException(status_code=404, detail="Child profile not found")

    reply, tool_calls = await run_agent(req.child_id, req.message)
    return ChatResponse(reply=reply, tool_calls=tool_calls)
