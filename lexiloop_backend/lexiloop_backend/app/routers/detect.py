"""
routers/detect.py — wraps the existing HandwritingAnalyzer (analyzer.py)
in a FastAPI endpoint. A parent/teacher uploads a photo of the child's
handwriting; the analyzer returns a full DyslexiaReport; we persist the
key metrics to that child's MongoDB profile so the chat agent and
dashboard can use them.
"""

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.auth import get_current_user
from app.config import settings
from app.database import child_profiles_collection, sessions_collection
from app.schemas import DetectionSummary
from app.ai.handwriting.analyzer import HandwritingAnalyzer

router = APIRouter(prefix="/detect", tags=["handwriting"])

# Loaded once at import time — CNN inference is <5ms on CPU per model.py's
# own docstring, so a single shared instance is fine for a demo/small app.
_analyzer = HandwritingAnalyzer(model_path=settings.CNN_MODEL_PATH)


@router.post("/{child_id}", response_model=DetectionSummary)
async def detect_reversal(
    child_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    child = await child_profiles_collection().find_one({"_id": ObjectId(child_id)})
    if not child or child["parent_id"] != user["_id"]:
        raise HTTPException(status_code=404, detail="Child profile not found")

    image_bytes = await file.read()
    report = _analyzer.analyze(image_bytes)

    # Persist this session
    await sessions_collection().insert_one({
        "child_id": child_id,
        "type": "handwriting",
        "reversal_count": report.reversal_count,
        "reversal_percent": report.reversal_percent,
        "risk_score": report.overall_risk_score,
        "risk_label": report.risk_label,
        "reversals_found": report.reversals_found,
    })

    # Update the child's running profile: increment session count and
    # track which letters are most commonly reversed, most-recent-first.
    new_letters = [r["letter"] for r in report.reversals_found]
    await child_profiles_collection().update_one(
        {"_id": ObjectId(child_id)},
        {
            "$inc": {"total_sessions": 1},
            "$push": {"common_reversals": {"$each": new_letters, "$slice": -20}},
        },
    )

    return DetectionSummary(
        child_id=child_id,
        total_chars=report.total_chars,
        reversal_count=report.reversal_count,
        reversal_percent=report.reversal_percent,
        overall_risk_score=report.overall_risk_score,
        risk_label=report.risk_label,
        reversals_found=report.reversals_found,
        annotated_image_b64=report.annotated_image_b64,
    )
