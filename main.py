"""
LAN-Based Offline Media Server
FastAPI backend for serving media files over local Wi-Fi network.

Features (MVP):
- List all files in the './files' directory with metadata
- Stream/download individual files efficiently
- Proper error handling and HTTP status codes
- CORS disabled by default (LAN-only usage)
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import StreamingResponse, JSONResponse

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
APP_TITLE = "LAN Media Server"
APP_VERSION = "1.0.0"
FILES_DIRECTORY = Path("files")

# Ensure the files directory exists
FILES_DIRECTORY.mkdir(exist_ok=True)

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Offline media server for LAN-based Android streaming application",
)


# ----------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------
def get_file_metadata(path: Path) -> dict:
    """
    Extract metadata for a single file.
    """
    stat = path.stat()
    return {
        "name": path.name,
        "size": stat.st_size,                    # Size in bytes
        "lastModified": datetime.fromtimestamp(stat.st_mtime).isoformat(),  # ISO 8601 format
    }


def list_media_files() -> List[dict]:
    """
    Return metadata for all files in the FILES_DIRECTORY.
    Only regular files are included (no directories or hidden files).
    """
    files = []
    for item in FILES_DIRECTORY.iterdir():
        if item.is_file() and not item.name.startswith("."):
            files.append(get_file_metadata(item))
    # Sort by name for consistent ordering
    files.sort(key=lambda x: x["name"].lower())
    return files


async def file_generator(file_path: Path):
    """
    Asynchronous generator for streaming file content in chunks.
    Prevents loading large files entirely into memory.
    """
    chunk_size = 1024 * 1024  # 1 MB chunks
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                yield chunk
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading file: {str(e)}"
        )


# ----------------------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------------------
@app.get("/")
async def root():
    """
    Root endpoint – provides basic server status.
    Useful for quick connectivity testing from the Android app or browser.
    """
    return {
        "message": "LAN Media Server is running",
        "title": APP_TITLE,
        "version": APP_VERSION,
        "files_count": len(list_media_files()),
    }


@app.get("/api/files", response_model=List[dict])
async def get_file_list():
    """
    Retrieve metadata for all available media files.
    """
    try:
        files = list_media_files()
        return JSONResponse(content=files)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )


@app.get("/api/files/{filename}")
async def get_file(filename: str):
    """
    Stream or download a specific file.
    Uses StreamingResponse for efficient handling of large media files.
    """
    file_path = FILES_DIRECTORY / filename

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Determine media type (basic mapping)
    content_type_map = {
        ".mp4": "video/mp4",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
    }

    media_type = content_type_map.get(file_path.suffix.lower(), "application/octet-stream")

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{file_path.name}"',
    }

    return StreamingResponse(
        file_generator(file_path),
        media_type=media_type,
        headers=headers,
    )


# ----------------------------------------------------------------------
# Run Instructions (for reference)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    # Binds to all interfaces (0.0.0.0) so it's accessible on LAN
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)