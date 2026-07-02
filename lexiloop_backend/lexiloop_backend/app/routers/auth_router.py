"""
routers/auth_router.py — signup and login endpoints.
Issues JWTs that every other route (except /auth/*) requires.
"""

from fastapi import APIRouter, HTTPException

from app.auth import hash_password, verify_password, create_access_token
from app.database import users_collection
from app.schemas import SignupRequest, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
async def signup(req: SignupRequest):
    existing = await users_collection().find_one({"email": req.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_doc = {
        "email": req.email,
        "password_hash": hash_password(req.password),
        "name": req.name,
        "role": req.role,
        "child_ids": [],
    }
    await users_collection().insert_one(user_doc)

    token = create_access_token({"sub": req.email})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = await users_collection().find_one({"email": req.email})
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token({"sub": req.email})
    return TokenResponse(access_token=token)
