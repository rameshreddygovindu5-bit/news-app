"""
File Upload API — handles image uploads for articles and wishes.
Stores files in UPLOAD_DIR (local disk), serves via /uploads/ static route.
"""

import os
import uuid
import logging
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.config import get_settings
from app.models.models import AdminUser
from app.services.auth_service import get_current_user

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/upload", tags=["File Upload"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
MAX_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # bytes


def _ensure_upload_dir():
    """Create upload directory if it doesn't exist."""
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


@router.post("")
async def upload_image(
    file: UploadFile = File(...),
    user: AdminUser = Depends(get_current_user),
):
    """
    Upload an image file. Returns the URL path to use in articles/wishes.
    Supported: jpg, jpeg, png, gif, webp, svg (max 10MB).
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(content) // 1024 // 1024}MB). Max: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Generate unique filename
    upload_dir = _ensure_upload_dir()
    date_prefix = datetime.now().strftime("%Y%m")
    subdir = upload_dir / date_prefix
    subdir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
    file_path = subdir / unique_name

    # Write file
    with open(file_path, "wb") as f:
        f.write(content)

    # Return URL path (served by FastAPI static mount or nginx)
    url_path = f"/uploads/{date_prefix}/{unique_name}"

    logger.info(f"[UPLOAD] {user.username} uploaded {file.filename} → {url_path} ({len(content)} bytes)")

    return {
        "url": url_path,
        "filename": unique_name,
        "original_name": file.filename,
        "size": len(content),
        "content_type": file.content_type,
    }
