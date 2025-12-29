# LAN-Based Offline Media Server (FastAPI)

Scalable offline LAN media server for streaming files from nested folders without internet. Supports streaming and downloading files like videos(.mkv, .mp4), images, text, PDF, etc.

## Features
- Stream files with proper MIME types
- Download files with proper content 
- Offline/LAN-only
- No internet required

## Setup (after cloning this repo)
1. Install Python 3.10+ and dependencies:

pip install requirements.txt

2. Create `files` folder in the same directory as `main.py`
3. Add your files to `file` (e.g., vid1.mp4, song1.mp3, image1.jpg)
4. Run the server:

uvicorn main:app --host 0.0.0.0 --port 8000 --reload

## API Endpoints
- `/`: Server status
- `/api/files`: List files/folders
- `/api/files/{filename}`: Stream or download file

## Code Snippet for Server
```python
# main.py (full code provided in your query)