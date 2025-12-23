"""
LAN-Based Offline Media Server
FastAPI backend for serving media files over local Wi-Fi network.
"""

from datetime import datetime
from pathlib import Path
from typing import List
import mimetypes

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
APP_TITLE = "LAN Media Server"
APP_VERSION = "1.0.0"
FILES_DIRECTORY = Path("files")

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
    stat = path.stat()
    return {
        "name": path.name,
        "size": stat.st_size,
        "lastModified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def list_media_files() -> List[dict]:
    files = []
    for item in FILES_DIRECTORY.iterdir():
        if item.is_file() and not item.name.startswith("."):
            files.append(get_file_metadata(item))
    files.sort(key=lambda x: x["name"].lower())
    return files


def file_streamer(file_path: Path, chunk_size: int = 1024 * 1024):
    """
    Generator that streams files in chunks.
    Sync I/O is intentional and safe with StreamingResponse.
    """
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
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


@app.get("/api/files", response_model=List[dict])
async def get_file_list():
    try:
        return JSONResponse(content=list_media_files())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}",
        )


@app.get("/api/files/{filename}")
async def get_file(filename: str, download: bool = False):
    # Basic path traversal protection
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = FILES_DIRECTORY / filename

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    media_type, _ = mimetypes.guess_type(file_path.name)
    media_type = media_type or "application/octet-stream"

    file_size = file_path.stat().st_size
    disposition = "attachment" if download else "inline"

    headers = {
        "Content-Length": str(file_size),
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'{disposition}; filename="{file_path.name}"',
    }

    return StreamingResponse(
        file_streamer(file_path),
        media_type=media_type,
        headers=headers,
    )

# ----------------------------------------------------------------------
# Run Instructions
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
