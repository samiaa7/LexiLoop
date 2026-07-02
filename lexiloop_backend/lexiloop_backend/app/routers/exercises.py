"""
routers/exercises.py — generates a personalized reading exercise for a
child by pulling a level-appropriate story (via the same retrieval used
by the chat agent) and asking the LLM for comprehension questions
tailored to that child's known struggles.
"""

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from langchain_groq import ChatGroq

from app.auth import get_current_user
from app.config import settings
from app.database import child_profiles_collection
from app.schemas import ExerciseRequest, ExerciseOut
from app.ai.agent.tools import _load_story_index

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.post("", response_model=ExerciseOut)
async def generate_exercise(req: ExerciseRequest, user: dict = Depends(get_current_user)):
    child = await child_profiles_collection().find_one({"_id": ObjectId(req.child_id)})
    if not child or child["parent_id"] != user["_id"]:
        raise HTTPException(status_code=404, detail="Child profile not found")

    level = child.get("reading_level", "beginner")
    store = _load_story_index()
    results = store.similarity_search(level, k=1)
    if not results:
        raise HTTPException(status_code=500, detail="No stories available")

    doc = results[0]
    title = doc.metadata["title"]
    passage = doc.page_content

    llm = ChatGroq(model=settings.GROQ_MODEL, api_key=settings.GROQ_API_KEY, temperature=0.5)
    reversals = child.get("common_reversals", [])
    prompt = (
        f"Write exactly 3 short comprehension questions for a child at "
        f"reading level '{level}' about this story:\n\n{passage}\n\n"
        f"This child recently mixed up these letters: {reversals[-5:] or 'none noted'}. "
        f"Keep the questions simple, one per line, no numbering."
    )
    response = await llm.ainvoke(prompt)
    questions = [q.strip("- ").strip() for q in response.content.splitlines() if q.strip()]

    return ExerciseOut(
        passage_title=title,
        passage_text=passage,
        comprehension_questions=questions[:3],
        target_level=level,
    )
