"""
Gemini-powered license plate recognition.

Requires environment variable GEMINI_API_KEY. If present, this module can be used
to recognize a plate string from an image (base64 data URL or numpy array).
"""
from __future__ import annotations

import os
import io
import re
import json
import base64
from typing import Any, Dict, Optional, Tuple


def _prepare_image_bytes(image_data: Any) -> Tuple[bytes, str]:
    """Return (image_bytes, mime_type) from base64 data URL or numpy array or raw bytes."""
    # Base64 data URL
    if isinstance(image_data, str) and image_data.startswith("data:image"):
        header, b64 = image_data.split(",", 1)
        if ";base64" in header:
            mime = header.split(";")[0].split(":", 1)[1]
            return base64.b64decode(b64), mime
        else:
            mime = header.split(":", 1)[1]
            return image_data.encode("utf-8"), mime

    # Plain base64 without header
    if isinstance(image_data, str) and re.fullmatch(r"[A-Za-z0-9+/=\n\r]+", image_data[:80] or ""):
        try:
            return base64.b64decode(image_data), "image/png"
        except Exception:
            pass

    # Numpy array
    try:
        import numpy as np  # type: ignore
        import cv2  # type: ignore
        if isinstance(image_data, np.ndarray):
            success, buf = cv2.imencode('.png', image_data)
            if not success:
                raise ValueError("Failed to encode image to PNG")
            return buf.tobytes(), "image/png"
    except Exception:
        pass

    # Raw bytes assumed image
    if isinstance(image_data, (bytes, bytearray)):
        return bytes(image_data), "application/octet-stream"

    # PIL Image
    try:
        from PIL import Image  # type: ignore
        if isinstance(image_data, Image.Image):
            bio = io.BytesIO()
            image_data.save(bio, format='PNG')
            return bio.getvalue(), "image/png"
    except Exception:
        pass

    raise ValueError("Unsupported image_data format for Gemini recognition")


def _extract_plate_from_text(text: str) -> Optional[str]:
    """Heuristic extraction of plate-like token from text."""
    if not text:
        return None
    # Common international plate patterns: letters and digits, 4-10 chars typically
    candidates = re.findall(r"\b[A-Z0-9]{4,10}\b", text.upper())
    # Prefer those that mix letters and digits
    mixed = [c for c in candidates if re.search(r"[A-Z]", c) and re.search(r"[0-9]", c)]
    return (mixed or candidates or [None])[0]


def recognize_plate_with_gemini(image_data: Any, *, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash") -> Dict[str, Any]:
    """
    Use Gemini multimodal model to recognize a license plate.
    Returns dict: { success, plate, confidence, raw }
    """
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"success": False, "error": "GEMINI_API_KEY not set"}

    img_bytes, mime = _prepare_image_bytes(image_data)

    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        prompt = (
            "You are an ANPR assistant. Extract the vehicle license plate text from the provided image. "
            "If multiple plates are visible, choose the most prominent. "
            "Return a strict JSON object with keys: plate (string, uppercase, without spaces or dashes), "
            "confidence (number 0..1) and notes (string). No extra text."
        )

        parts = [
            prompt,
            {"mime_type": mime, "data": img_bytes},
        ]

        resp = model.generate_content(parts)
        raw_text = getattr(resp, "text", None) or (getattr(resp, 'candidates', None) and resp.candidates[0].content.parts[0].text)
        if not raw_text:
            raw_text = str(resp)

        # Try parse JSON
        plate = None
        confidence = 0.0
        try:
            data = json.loads(raw_text)
            plate = (data.get("plate") or "").upper().replace(" ", "").replace("-", "").replace("·", "")
            confidence = float(data.get("confidence") or 0.0)
        except Exception:
            # Heuristic fallback: extract first plate-like token
            plate = _extract_plate_from_text(raw_text)
            confidence = 0.7 if plate else 0.0

        return {
            "success": bool(plate),
            "plate": plate,
            "confidence": confidence,
            "raw": raw_text,
            "model": model_name,
            "method": "gemini",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
