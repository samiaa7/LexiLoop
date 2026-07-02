"""
routers/simplify.py — thin FastAPI wrapper around ai/simplify_engine.py
(the logic ported directly from Dyslexia Buddy's app.py).
"""

from fastapi import APIRouter, HTTPException, Depends

from app.auth import get_current_user
from app.schemas import TextRequest, SimplifyResponse
from app.ai import simplify_engine

router = APIRouter(prefix="/simplify", tags=["text"])


@router.post("", response_model=SimplifyResponse)
async def simplify(req: TextRequest, user: dict = Depends(get_current_user)):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text must not be empty.")
    if len(text) > 5_000:
        raise HTTPException(status_code=400, detail="Text too long (max 5,000 chars).")

    ml_out = simplify_engine.ml_simplify(text)
    rule_out = simplify_engine.rule_simplify(text)
    model = simplify_engine.MODEL_NAME if simplify_engine.is_model_ready() else "rule-based only"

    return SimplifyResponse(ml_simplified=ml_out, rule_simplified=rule_out, model_used=model)


@router.post("/readability")
async def readability(req: TextRequest, user: dict = Depends(get_current_user)):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text must not be empty.")
    return simplify_engine.compute_readability(text)
