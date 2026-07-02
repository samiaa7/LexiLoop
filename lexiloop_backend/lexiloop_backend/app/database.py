"""
database.py — MongoDB Atlas connection + collection accessors.

Uses motor (the async MongoDB driver) since FastAPI endpoints are async.
Collections:
  users            — parent/teacher accounts (login credentials)
  child_profiles   — one doc per child, holds the evolving reading profile
  sessions         — one doc per reading/handwriting session
  reading_exercises — generated exercises, linked to a child_profile
"""

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        if not settings.MONGODB_URI:
            raise RuntimeError(
                "MONGODB_URI is not set. Add it to your .env file."
            )
        _client = AsyncIOMotorClient(settings.MONGODB_URI)
    return _client


def get_db():
    return get_client()[settings.MONGODB_DB_NAME]


def users_collection():
    return get_db()["users"]


def child_profiles_collection():
    return get_db()["child_profiles"]


def sessions_collection():
    return get_db()["sessions"]


def exercises_collection():
    return get_db()["reading_exercises"]
