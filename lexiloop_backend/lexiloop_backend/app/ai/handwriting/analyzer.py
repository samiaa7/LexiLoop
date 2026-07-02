"""
analyzer.py — Dyslexic Handwriting CV Pipeline
===============================================
Pipeline:
  1. Preprocess image      (grayscale, denoise, adaptive threshold)
  2. Segment lines         (horizontal projection profile)
  3. Segment characters    (contour-based per line)
  4. Classify each char    (DyslexiaCNN or rule-based fallback)
  5. Extract dyslexia markers:
       - Letter reversals  (b/d, p/q, n/u, m/w, s/z)
       - Size inconsistency (height variance across chars)
       - Spacing irregularity (gap variance between chars)
       - Baseline deviation (vertical drift of char centroids)
       - Stroke width variance (thin vs thick strokes in same word)
  6. Annotate image        (draw bounding boxes, labels, heatmap)
  7. Return structured report

Usage:
  from analyzer import HandwritingAnalyzer
  analyzer = HandwritingAnalyzer(model_path="model.pth")
  report   = analyzer.analyze("sample.jpg")
"""

from __future__ import annotations

import io
import json
import logging
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try loading the CNN; fall back gracefully if not available
# ---------------------------------------------------------------------------
try:
    import torch
    import torchvision.transforms as T
    from model import DyslexiaCNN, CLASSES, DYSLEXIA_CONFUSIONS, load_model, predict_letter
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    logger.warning("PyTorch not available — using heuristic-only mode.")
    CLASSES = list("abcdefghijklmnopqrstuvwxyz")
    DYSLEXIA_CONFUSIONS = {
        "b": ["d","p","q"], "d": ["b","p","q"],
        "p": ["b","d","q"], "q": ["b","d","p"],
        "n": ["u"], "u": ["n"], "m": ["w"], "w": ["m"],
        "s": ["z"], "z": ["s"],
    }


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CharResult:
    """Result for a single segmented character."""
    bbox: tuple[int,int,int,int]        # x, y, w, h  (in original image coords)
    predicted_letter: str
    confidence: float
    top3: list[tuple[str, float]]       # [(letter, prob), ...]
    is_reversal: bool
    reversal_pair: Optional[str]        # the letter it was confused with
    line_idx: int
    char_idx: int


@dataclass
class LineMetrics:
    """Spatial metrics computed per text line."""
    line_idx: int
    char_heights: list[float]
    char_gaps: list[float]
    baseline_y_values: list[float]
    height_cv: float          # coefficient of variation (std/mean) → inconsistency
    gap_cv: float
    baseline_drift: float     # std of centroid y positions normalised by mean height


@dataclass
class DyslexiaReport:
    """Full structured report returned by HandwritingAnalyzer.analyze()."""
    # --- counts ---
    total_chars: int
    reversal_count: int
    reversal_percent: float

    # --- spatial markers ---
    size_inconsistency_score: float     # 0–1, higher = more inconsistent
    spacing_irregularity_score: float
    baseline_drift_score: float
    overall_risk_score: float           # weighted composite 0–1

    # --- risk label ---
    risk_label: str                     # "Low" / "Moderate" / "High"
    risk_color: str                     # hex for UI

    # --- details ---
    reversals_found: list[dict]         # [{letter, confused_with, bbox}, ...]
    line_metrics: list[dict]
    char_results: list[dict]

    # --- images (base64 PNG) ---
    annotated_image_b64: str
    heatmap_image_b64: str

    # --- meta ---
    model_used: str
    image_size: tuple[int,int]


# ---------------------------------------------------------------------------
# Image preprocessing
# ---------------------------------------------------------------------------

def preprocess(img_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Convert to grayscale, denoise, and apply adaptive thresholding.
    Returns (gray, binary) both at original resolution.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Mild denoising — preserve thin strokes
    denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7,
                                         searchWindowSize=21)

    # Adaptive threshold — handles uneven lighting / paper texture
    binary = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=31, C=10,
    )

    # Remove ruled notebook lines / margin lines. Without this, long straight
    # lines bridge adjacent rows of handwriting (and the margin rule bridges
    # words on the left edge) into single giant connected components, which
    # breaks line segmentation and character segmentation downstream.
    binary = remove_ruled_lines(binary)

    # Morphological closing to connect broken strokes (common in dyslexic handwriting)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    return gray, binary


def remove_ruled_lines(binary: np.ndarray) -> np.ndarray:
    """
    Detect and erase long straight horizontal/vertical lines (notebook
    rule lines, margin lines) from a binary (foreground=255) image.

    Uses morphological opening with long thin kernels: a kernel that's
    long in one axis and 1px in the other only survives the opening where
    the foreground is itself long and thin in that direction — i.e. ruled
    lines, not handwritten strokes. The result is dilated slightly to
    catch anti-aliased edges, then subtracted from the original mask.
    """
    h, w = binary.shape

    # Horizontal ruled lines: kernel width scales with image width so this
    # works regardless of resolution; length picked to exceed letter widths
    # but stay shorter than a full ruled line.
    horiz_len = max(25, w // 30)
    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (horiz_len, 1))
    horiz_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horiz_kernel)
    horiz_lines = cv2.dilate(horiz_lines, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3)))

    # Vertical margin lines (e.g. the red/pink margin rule on notebook paper).
    vert_len = max(25, h // 30)
    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vert_len))
    vert_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vert_kernel)
    vert_lines = cv2.dilate(vert_lines, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1)))

    ruled = cv2.bitwise_or(horiz_lines, vert_lines)
    return cv2.subtract(binary, ruled)


# ---------------------------------------------------------------------------
# Line segmentation
# ---------------------------------------------------------------------------

def segment_lines(binary: np.ndarray,
                  min_line_height: int = 10) -> list[tuple[int,int]]:
    """
    Use horizontal projection profile to find text line bands.
    Returns list of (y_start, y_end) row intervals.
    """
    proj = binary.sum(axis=1)           # sum of white pixels per row

    # Smooth projection to merge close rows
    kernel_size = max(3, binary.shape[0] // 80)
    proj_smooth = np.convolve(proj, np.ones(kernel_size)/kernel_size, mode='same')

    threshold = proj_smooth.max() * 0.05
    in_line   = proj_smooth > threshold

    lines: list[tuple[int,int]] = []
    start = None
    for i, active in enumerate(in_line):
        if active and start is None:
            start = i
        elif not active and start is not None:
            if i - start >= min_line_height:
                lines.append((start, i))
            start = None
    if start is not None and binary.shape[0] - start >= min_line_height:
        lines.append((start, binary.shape[0]))

    return lines


# ---------------------------------------------------------------------------
# Character segmentation
# ---------------------------------------------------------------------------

def segment_characters(
    binary_line: np.ndarray,
    y_offset: int,
    line_idx: int,
    min_w: int = 5,
    min_h: int = 8,
    max_w_ratio: float = 0.4,
) -> list[tuple[int,int,int,int]]:
    """
    Find individual character bounding boxes in a single line strip.
    Returns list of (x, y, w, h) in full-image coordinates.
    """
    contours, _ = cv2.findContours(binary_line, cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[tuple[int,int,int,int]] = []
    W = binary_line.shape[1]

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < min_w or h < min_h:
            continue
        if w > W * max_w_ratio:     # skip very wide blobs (likely ligatures / smudges)
            continue
        boxes.append((x, y + y_offset, w, h))

    # Sort left → right
    boxes.sort(key=lambda b: b[0])
    return boxes


def segment_characters_global(
    binary: np.ndarray,
    min_w: int = 5,
    min_h: int = 8,
    max_w_ratio: float = 0.4,
) -> list[tuple[int,int,int,int]]:
    """
    Find character bounding boxes on the WHOLE cleaned binary image at
    once, instead of pre-slicing into line bands first.

    Why: projection-profile line bands assume rows of text have a clean
    gap between them. Real handwriting often has ascenders/descenders
    that bridge adjacent rows, so a bad line-band boundary can silently
    swallow many rows into one band — and character segmentation run on
    a giant multi-row band produces far fewer, much larger, mostly-
    filtered-out contours. Segmenting globally avoids depending on line
    boundaries being correct; lines are assigned afterward from the
    character boxes themselves (see cluster_boxes_into_lines).
    """
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[tuple[int,int,int,int]] = []
    W = binary.shape[1]

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < min_w or h < min_h:
            continue
        if w > W * max_w_ratio:     # skip very wide blobs (likely ligatures / smudges)
            continue
        boxes.append((x, y, w, h))

    return boxes


def cluster_boxes_into_lines(
    boxes: list[tuple[int,int,int,int]],
    gap_factor: float = 0.6,
) -> list[list[tuple[int,int,int,int]]]:
    """
    Group character boxes into text lines using their vertical centroids.

    Approach: sort boxes by y-centroid, then walk through them and start
    a new line whenever the gap to the next centroid exceeds a threshold
    derived from the typical character height seen so far. This is more
    robust than a global projection-profile threshold because it adapts
    to the actual character sizes in the image rather than assuming a
    fixed gap works for the whole page.

    Returns a list of lines, each a list of (x, y, w, h) boxes sorted
    left-to-right.
    """
    if not boxes:
        return []

    # Sort by vertical centroid
    by_y = sorted(boxes, key=lambda b: b[1] + b[3] / 2)
    heights = [b[3] for b in by_y]
    median_h = float(np.median(heights)) if heights else 10.0
    threshold = max(4.0, median_h * gap_factor)

    lines: list[list[tuple[int,int,int,int]]] = []
    current: list[tuple[int,int,int,int]] = [by_y[0]]
    prev_cy = by_y[0][1] + by_y[0][3] / 2

    for box in by_y[1:]:
        cy = box[1] + box[3] / 2
        if abs(cy - prev_cy) > threshold:
            lines.append(current)
            current = [box]
        else:
            current.append(box)
        prev_cy = cy
    lines.append(current)

    # Sort each line left → right, and sort lines top → bottom
    lines = [sorted(line, key=lambda b: b[0]) for line in lines]
    lines.sort(key=lambda line: min(b[1] for b in line))

    return lines


# ---------------------------------------------------------------------------
# Stroke width transform (SWT) approximation
# ---------------------------------------------------------------------------

def mean_stroke_width(binary_patch: np.ndarray) -> float:
    """
    Approximate mean stroke width using distance transform.
    SWT ≈ 2 × mean distance-transform value at skeleton pixels.
    """
    if binary_patch.sum() == 0:
        return 0.0
    dist = cv2.distanceTransform(binary_patch, cv2.DIST_L2, 5)
    skeleton = cv2.ximgproc.thinning(binary_patch) if hasattr(cv2, 'ximgproc') else binary_patch
    vals = dist[skeleton > 0]
    return float(vals.mean() * 2) if len(vals) else 0.0


# ---------------------------------------------------------------------------
# CNN inference helpers
# ---------------------------------------------------------------------------

def _prepare_tensor(patch: np.ndarray) -> "torch.Tensor":
    """Resize a binary character patch to 28×28 and convert to tensor."""
    resized = cv2.resize(patch, (28, 28), interpolation=cv2.INTER_AREA)
    pil     = Image.fromarray(resized)
    tf = T.Compose([
        T.ToTensor(),
        T.Normalize((0.1722,), (0.3310,)),
    ])
    return tf(pil).unsqueeze(0)      # 1×1×28×28


# ---------------------------------------------------------------------------
# Heuristic letter predictor (used when model.pth not available)
# ---------------------------------------------------------------------------

_COMMON_LETTERS = list("etaoinshrdlu")

def heuristic_predict(patch: np.ndarray) -> list[tuple[str, float]]:
    """
    Very rough heuristic: use aspect ratio + pixel density to bias predictions.
    Returns top-3 (letter, pseudo-probability) pairs.
    Only used when the CNN model is unavailable.
    """
    h, w = patch.shape
    ratio = w / max(h, 1)
    density = patch.sum() / max(patch.size, 1) / 255

    # Wide, dense → likely m or w
    if ratio > 1.2 and density > 0.4:
        return [("m", 0.5), ("w", 0.3), ("n", 0.2)]
    # Tall, narrow → likely l, i, or d
    if ratio < 0.5:
        return [("l", 0.4), ("i", 0.3), ("d", 0.3)]
    # Default: sample from common letters
    import random
    random.shuffle(_COMMON_LETTERS)
    letters = _COMMON_LETTERS[:3]
    probs   = [0.5, 0.3, 0.2]
    return list(zip(letters, probs))


# ---------------------------------------------------------------------------
# Spatial metric helpers
# ---------------------------------------------------------------------------

def coefficient_of_variation(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    arr  = np.array(values, dtype=float)
    mean = arr.mean()
    return float(arr.std() / mean) if mean > 0 else 0.0


def baseline_drift(centroids_y: list[float], heights: list[float]) -> float:
    """Std of vertical centroid positions normalised by mean char height."""
    if len(centroids_y) < 2:
        return 0.0
    arr  = np.array(centroids_y, dtype=float)
    mean_h = np.mean(heights) if heights else 1.0
    return float(arr.std() / mean_h)


# ---------------------------------------------------------------------------
# Annotation helpers
# ---------------------------------------------------------------------------

def _b64_png(img_bgr: np.ndarray) -> str:
    import base64
    ok, buf = cv2.imencode(".png", img_bgr)
    return base64.b64encode(buf.tobytes()).decode() if ok else ""


def annotate_image(
    img_bgr: np.ndarray,
    char_results: list[CharResult],
) -> np.ndarray:
    """
    Draw bounding boxes on a copy of the image:
      - Red  box + label  → reversal detected
      - Green box         → normal
    """
    out = img_bgr.copy()
    for ch in char_results:
        x, y, w, h = ch.bbox
        if ch.is_reversal:
            color  = (0, 0, 220)          # red (BGR)
            label  = f"{ch.predicted_letter}/{ch.reversal_pair}?"
            thick  = 2
        else:
            color  = (34, 139, 34)        # green
            label  = ch.predicted_letter
            thick  = 1

        cv2.rectangle(out, (x, y), (x+w, y+h), color, thick)
        cv2.putText(out, label, (x, max(y-4, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)

    return out


def build_heatmap(
    img_bgr: np.ndarray,
    char_results: list[CharResult],
) -> np.ndarray:
    """
    Overlay a soft red heatmap on regions with detected reversals or
    low-confidence predictions (confidence < 0.5).
    """
    H, W = img_bgr.shape[:2]
    heat  = np.zeros((H, W), dtype=np.float32)
    sigma = 30

    for ch in char_results:
        x, y, w, h = ch.bbox
        cx, cy = x + w // 2, y + h // 2
        intensity = 0.0
        if ch.is_reversal:
            intensity += 0.8
        if ch.confidence < 0.5:
            intensity += 0.4
        if intensity == 0:
            continue
        # Gaussian blob
        y_idx, x_idx = np.ogrid[:H, :W]
        blob = intensity * np.exp(-((x_idx-cx)**2 + (y_idx-cy)**2) / (2*sigma**2))
        heat += blob.astype(np.float32)

    heat = np.clip(heat, 0, 1)
    heat_u8  = (heat * 255).astype(np.uint8)
    colormap = cv2.applyColorMap(heat_u8, cv2.COLORMAP_JET)
    result   = cv2.addWeighted(img_bgr, 0.6, colormap, 0.4, 0)
    return result


# ---------------------------------------------------------------------------
# Main analyzer class
# ---------------------------------------------------------------------------

class HandwritingAnalyzer:
    """
    End-to-end dyslexic handwriting analysis pipeline.

    Parameters
    ----------
    model_path : path to trained model.pth (optional).
                 Falls back to heuristic mode if not found.
    """

    def __init__(self, model_path: str | Path = "model.pth") -> None:
        self.model      = None
        self.model_name = "heuristic"

        if _TORCH_AVAILABLE:
            p = Path(model_path)
            if p.exists():
                try:
                    self.model      = load_model(p)
                    self.model_name = f"DyslexiaCNN ({p.name})"
                    logger.info("CNN model loaded from %s", p)
                except Exception as exc:
                    logger.warning("Could not load model: %s", exc)
            else:
                logger.warning("model.pth not found — run: python model.py --train")
        else:
            logger.warning("PyTorch unavailable; heuristic mode active.")

    # ------------------------------------------------------------------
    def analyze(self, image_input: str | Path | bytes | np.ndarray) -> DyslexiaReport:
        """
        Run the full pipeline on an image.

        Accepts:
          - file path (str or Path)
          - raw bytes (JPEG/PNG)
          - numpy array (BGR, as from cv2.imread)
        """
        img_bgr = self._load_image(image_input)
        H, W    = img_bgr.shape[:2]

        # 1. Preprocess
        gray, binary = preprocess(img_bgr)

        # 2. Segment characters globally (NOT pre-sliced by line band).
        #    Real handwriting routinely has ascenders/descenders that
        #    vertically overlap between rows, so projection-profile line
        #    bands can't be trusted as hard slice boundaries — slicing
        #    first and segmenting characters within each slice causes
        #    massive under-segmentation whenever two rows touch. Instead,
        #    find all character boxes on the whole page at once, then
        #    group them into lines afterward using their y-centroids.
        all_boxes = segment_characters_global(binary)

        # 3. Cluster character boxes into lines by y-centroid
        line_assignments = cluster_boxes_into_lines(all_boxes)
        if not line_assignments:
            line_assignments = []

        # 4. Classify characters & compute per-line spatial metrics
        all_chars: list[CharResult] = []
        line_metrics_list: list[LineMetrics] = []

        for line_idx, boxes in enumerate(line_assignments):
            if not boxes:
                continue

            char_heights: list[float] = []
            char_gaps:    list[float] = []
            centroids_y:  list[float] = []

            prev_x_end = None
            for char_idx, (x, y, w, h) in enumerate(boxes):
                # Gap between consecutive chars
                if prev_x_end is not None:
                    char_gaps.append(float(x - prev_x_end))
                prev_x_end = x + w

                char_heights.append(float(h))
                centroids_y.append(float(y + h / 2))

                # Extract patch from binary image
                patch = binary[y:y+h, x:x+w]

                # Classify
                top3 = self._classify(patch)
                predicted, confidence = top3[0]

                # Check reversal
                is_rev = False
                rev_pair = None
                for alt_letter, alt_prob in top3[1:]:
                    if alt_prob > 0.25:
                        if alt_letter in DYSLEXIA_CONFUSIONS.get(predicted, []):
                            is_rev   = True
                            rev_pair = alt_letter
                            break
                        if predicted in DYSLEXIA_CONFUSIONS.get(alt_letter, []):
                            is_rev   = True
                            rev_pair = alt_letter
                            break

                all_chars.append(CharResult(
                    bbox=(x, y, w, h),
                    predicted_letter=predicted,
                    confidence=confidence,
                    top3=top3,
                    is_reversal=is_rev,
                    reversal_pair=rev_pair,
                    line_idx=line_idx,
                    char_idx=char_idx,
                ))

            # Line-level spatial metrics
            h_cv  = coefficient_of_variation(char_heights)
            g_cv  = coefficient_of_variation(char_gaps) if char_gaps else 0.0
            b_drift = baseline_drift(centroids_y, char_heights)

            line_metrics_list.append(LineMetrics(
                line_idx=line_idx,
                char_heights=char_heights,
                char_gaps=char_gaps,
                baseline_y_values=centroids_y,
                height_cv=round(h_cv, 4),
                gap_cv=round(g_cv, 4),
                baseline_drift=round(b_drift, 4),
            ))

        # 4. Aggregate scores
        total_chars    = len(all_chars)
        reversals      = [c for c in all_chars if c.is_reversal]
        rev_count      = len(reversals)
        rev_percent    = round(rev_count / max(total_chars, 1) * 100, 1)

        # Normalise spatial markers to [0, 1] using empirical thresholds
        all_h_cvs = [m.height_cv    for m in line_metrics_list]
        all_g_cvs = [m.gap_cv       for m in line_metrics_list]
        all_drifts= [m.baseline_drift for m in line_metrics_list]

        size_score    = min(1.0, np.mean(all_h_cvs)  / 0.35) if all_h_cvs  else 0.0
        spacing_score = min(1.0, np.mean(all_g_cvs)  / 0.60) if all_g_cvs  else 0.0
        drift_score   = min(1.0, np.mean(all_drifts) / 0.30) if all_drifts else 0.0
        reversal_score = min(1.0, rev_percent / 30.0)

        # Weighted composite
        overall = (
            0.35 * reversal_score +
            0.25 * size_score     +
            0.25 * spacing_score  +
            0.15 * drift_score
        )
        overall = round(float(overall), 3)

        if overall >= 0.60:
            risk_label, risk_color = "High",     "#E24B4A"
        elif overall >= 0.35:
            risk_label, risk_color = "Moderate", "#F59E0B"
        else:
            risk_label, risk_color = "Low",      "#22C55E"

        # 5. Annotate
        annotated   = annotate_image(img_bgr, all_chars)
        heatmap_img = build_heatmap(img_bgr, all_chars)

        # 6. Serialise
        reversals_found = [
            {
                "letter":        c.predicted_letter,
                "confused_with": c.reversal_pair,
                "confidence":    round(c.confidence, 3),
                "bbox":          list(c.bbox),
            }
            for c in reversals
        ]

        return DyslexiaReport(
            total_chars=total_chars,
            reversal_count=rev_count,
            reversal_percent=rev_percent,
            size_inconsistency_score=round(float(size_score),    3),
            spacing_irregularity_score=round(float(spacing_score), 3),
            baseline_drift_score=round(float(drift_score),       3),
            overall_risk_score=overall,
            risk_label=risk_label,
            risk_color=risk_color,
            reversals_found=reversals_found,
            line_metrics=[asdict(m) for m in line_metrics_list],
            char_results=[
                {
                    "bbox":             list(c.bbox),
                    "predicted_letter": c.predicted_letter,
                    "confidence":       round(c.confidence, 3),
                    "top3":             [(l, round(p,3)) for l,p in c.top3],
                    "is_reversal":      c.is_reversal,
                    "reversal_pair":    c.reversal_pair,
                    "line_idx":         c.line_idx,
                    "char_idx":         c.char_idx,
                }
                for c in all_chars
            ],
            annotated_image_b64=_b64_png(annotated),
            heatmap_image_b64=_b64_png(heatmap_img),
            model_used=self.model_name,
            image_size=(W, H),
        )

    # ------------------------------------------------------------------
    def _load_image(self, src) -> np.ndarray:
        if isinstance(src, np.ndarray):
            return src
        if isinstance(src, (str, Path)):
            img = cv2.imread(str(src))
            if img is None:
                raise ValueError(f"Could not read image: {src}")
            return img
        if isinstance(src, bytes):
            arr = np.frombuffer(src, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image bytes.")
            return img
        raise TypeError(f"Unsupported image type: {type(src)}")

    def _classify(self, patch: np.ndarray) -> list[tuple[str, float]]:
        if self.model is not None and _TORCH_AVAILABLE:
            try:
                tensor = _prepare_tensor(patch)
                return predict_letter(self.model, tensor, top_k=3)
            except Exception as exc:
                logger.debug("CNN inference error: %s", exc)
        return heuristic_predict(patch)
