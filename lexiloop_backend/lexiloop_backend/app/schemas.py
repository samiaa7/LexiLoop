"""
schemas.py — Pydantic models shared across routers.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# --- Auth ---

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = Field(default="parent", description="'parent' or 'teacher'")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Child profile ---

class ChildProfileCreate(BaseModel):
    name: str
    age: int
    reading_level: str = Field(default="beginner")


class ChildProfileOut(BaseModel):
    id: str
    name: str
    age: int
    reading_level: str
    total_sessions: int = 0
    common_reversals: list[str] = []
    mood_trend: list[str] = []


# --- Handwriting detection ---

class DetectionSummary(BaseModel):
    child_id: str
    total_chars: int
    reversal_count: int
    reversal_percent: float
    overall_risk_score: float
    risk_label: str
    reversals_found: list[dict]
    annotated_image_b64: str


# --- Chat / agent ---

class ChatRequest(BaseModel):
    child_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[str] = []


# --- Text simplification (reused from Dyslexia Buddy) ---

class TextRequest(BaseModel):
    text: str


class SimplifyResponse(BaseModel):
    ml_simplified: str
    rule_simplified: str
    model_used: str


# --- Reading exercises ---

class ExerciseRequest(BaseModel):
    child_id: str


class ExerciseOut(BaseModel):
    passage_title: str
    passage_text: str
    comprehension_questions: list[str]
    target_level: str
