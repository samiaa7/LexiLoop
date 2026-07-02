"""
ai/agent/tools.py — the four tools the LangChain reading-tutor agent
can call:
  1. simplify_text        — reuses Dyslexia Buddy's T5 pipeline
  2. retrieve_story        — RAG lookup over the local story library
  3. log_mood               — records the child's mood/frustration this turn
  4. update_child_profile   — writes an evolving summary back to MongoDB

Each tool is a plain async function wrapped with @tool so LangChain's
agent can call it by name. child_id is threaded through via closures
built in agent.py (create_tools_for_child), since a single global tool
can't know which child's session it's operating on.
"""

from pathlib import Path
from bson import ObjectId
from langchain_core.tools import tool
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from app.ai import simplify_engine
from app.database import child_profiles_collection, sessions_collection

STORIES_DIR = Path(__file__).parent / "stories"

_vectorstore: FAISS | None = None


def _load_story_index() -> FAISS:
    """Build (once) an in-memory FAISS index over the local story files."""
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    texts, metadatas = [], []
    for path in sorted(STORIES_DIR.glob("*.txt")):
        content = path.read_text(encoding="utf-8")
        title_line = content.splitlines()[0].replace("Title:", "").strip()
        texts.append(content)
        metadatas.append({"title": title_line, "source": path.name})

    _vectorstore = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
    return _vectorstore


def create_tools_for_child(child_id: str):
    """
    Returns the list of tools bound to a specific child_id, so the agent
    always reads/writes the correct profile without the LLM needing to
    pass child_id as an argument on every call.
    """

    @tool
    async def simplify_text(text: str) -> str:
        """Simplify a piece of text into easier words and shorter sentences,
        for a child who struggles with reading. Use this whenever the child
        or the flow asks to make something easier to read."""
        return simplify_engine.ml_simplify(text)

    @tool
    async def retrieve_story(topic_or_level: str) -> str:
        """Retrieve a short children's story from the story library, given
        a topic or a reading level (beginner/intermediate/advanced). Returns
        the story text plus its title, for the tutor to read with the child
        or to generate comprehension questions from."""
        store = _load_story_index()
        results = store.similarity_search(topic_or_level, k=1)
        if not results:
            return "No matching story found."
        doc = results[0]
        return f"Title: {doc.metadata['title']}\n\n{doc.page_content}"

    @tool
    async def log_mood(mood: str, note: str = "") -> str:
        """Log the child's current mood or frustration level during this
        session, e.g. 'frustrated', 'confident', 'bored', 'excited'. Call
        this whenever the child expresses how they're feeling about the
        reading exercise."""
        await child_profiles_collection().update_one(
            {"_id": ObjectId(child_id)},
            {"$push": {"mood_trend": {"$each": [mood], "$slice": -20}}},
        )
        await sessions_collection().insert_one({
            "child_id": child_id, "type": "mood_log", "mood": mood, "note": note,
        })
        return f"Logged mood: {mood}"

    @tool
    async def update_child_profile(summary: str) -> str:
        """Update this child's evolving profile summary with new
        observations from this conversation (e.g. topics they enjoy,
        specific struggles noticed, encouragement that worked well). This
        summary is shown to the tutor agent in future sessions so it can
        remember the child across conversations."""
        await child_profiles_collection().update_one(
            {"_id": ObjectId(child_id)},
            {"$set": {"profile_summary": summary}},
        )
        return "Profile updated."

    return [simplify_text, retrieve_story, log_mood, update_child_profile]
