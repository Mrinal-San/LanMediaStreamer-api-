"""
LAN-Based Offline Media Server (FastAPI)
Supports streaming, downloading, and resume for large files (videos, etc.)
Works perfectly with the Android app.
"""

from datetime import datetime
from pathlib import Path
from typing import List
import mimetypes

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import StreamingResponse, JSONResponse

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
APP_TITLE = "LAN Media Server"
APP_VERSION = "1.0.0"

# Folder where your media files are stored
FILES_DIRECTORY = Path("files")
FILES_DIRECTORY.mkdir(exist_ok=True)

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Offline LAN media server for Android streaming app",
)

# ----------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------
def get_file_metadata(path: Path) -> dict:
    """Get metadata for a file."""
    stat = path.stat()
    return {
        "name": path.name,
        "size": stat.st_size,
        "lastModified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }

def list_media_files() -> List[dict]:
    """List all media files in the root directory."""
    files = []
    for item in FILES_DIRECTORY.iterdir():
        if item.is_file() and not item.name.startswith("."):
            files.append(get_file_metadata(item))
    files.sort(key=lambda x: x["name"].lower())
    return files

def stream_full_file(file_path: Path, chunk_size: int = 1024 * 1024):
    """Stream the entire file."""
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            yield chunk

def stream_range(file_path: Path, start: int, end: int, chunk_size: int = 8192):
    """Stream a byte range from the file."""
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            chunk = f.read(read_size)
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk

# ----------------------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "message": "LAN Media Server is running",
        "title": APP_TITLE,
        "version": APP_VERSION,
        "files_count": len(list_media_files()),
    }

@app.get("/api/files")
async def get_file_list():
    """Return list of all files in the media folder."""
    try:
        return JSONResponse(content=list_media_files())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )

@app.get("/api/files/{filename:path}")
async def get_file(filename: str, request: Request, download: bool = False):
    """Stream or download a file with resume support."""
    # Security: prevent path traversal
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = FILES_DIRECTORY / filename

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    file_size = file_path.stat().st_size

    # Guess MIME type
    media_type, _ = mimetypes.guess_type(file_path.name)
    media_type = media_type or "application/octet-stream"

    disposition = "attachment" if download else "inline"

    base_headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'{disposition}; filename="{file_path.name}"',
    }

    range_header = request.headers.get("Range")

    if range_header:
        # Parse Range header: "bytes=0-" or "bytes=12345-"
        try:
            if not range_header.startswith("bytes="):
                raise ValueError("Invalid unit")

            range_str = range_header[6:].strip()
            start_str, end_str = (range_str.split("-") + [""])[:2]

            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1

            if start >= file_size or start < 0 or (end_str and end < start):
                raise HTTPException(status_code=416, detail="Range not satisfiable")

            length = end - start + 1

            headers = {
                **base_headers,
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(length),
            }

            return StreamingResponse(
                stream_range(file_path, start, end),
                status_code=206,  # Partial Content
                headers=headers,
                media_type=media_type,
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Malformed Range header")
        except Exception as e:
            raise HTTPException(status_code=416, detail=f"Range error: {str(e)}")

    # Full file download (no Range header)
    headers = {
        **base_headers,
        "Content-Length": str(file_size),
    }

    return StreamingResponse(
        stream_full_file(file_path),
        status_code=200,
        headers=headers,
        media_type=media_type,
    )

# ----------------------------------------------------------------------
# Run Server
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print(f"{APP_TITLE} v{APP_VERSION} starting...")
    print(f"Serving files from: {FILES_DIRECTORY.resolve()}")
    print("Access from LAN devices: http://YOUR_PC_IP:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)