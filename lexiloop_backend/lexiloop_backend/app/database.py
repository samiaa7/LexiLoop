from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        if not settings.MONGODB_URI:
            raise RuntimeError(
                "MONGODB_URI is not set"
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
