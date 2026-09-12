"""Meet tab audio -> the same transcribe-and-post pipeline (step 3).

    python audio/chunk_server.py      # http://localhost:3100 in Chrome

Serves audio/capture.html, which captures the Google Meet tab with
getDisplayMedia and POSTs a self-contained 10-second webm to /chunk.
Each chunk goes through ChunkPipeline, exactly as file and mic mode do.
"""

import sys
from pathlib import Path

from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import FileResponse
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from transcribe import SERVER, ChunkPipeline, iso_now, post_session_start, send  # noqa: E402

HERE = Path(__file__).resolve().parent
app = FastAPI(title="podium-coach tab capture")
PIPE = {"pipeline": None}


@app.get("/")
def page():
    return FileResponse(HERE / "capture.html")


@app.post("/start")
def start(outline: str = Form(None)):
    PIPE["pipeline"] = ChunkPipeline()
    outline_path = HERE.parent / outline if outline else None
    if outline_path and outline_path.exists():
        post_session_start(outline_path)
    print("new session, posting to %s" % SERVER, flush=True)
    return {"ok": True, "server": SERVER}


@app.post("/chunk")
async def chunk(audio: UploadFile = File(...), start: float = Form(...), end: float = Form(...)):
    if PIPE["pipeline"] is None:
        PIPE["pipeline"] = ChunkPipeline()
    body = await audio.read()
    try:
        ev = PIPE["pipeline"].handle(body, start, end, content_type="audio/webm")
    except Exception as e:                      # a bad chunk never stops the talk
        print("chunk failed, continuing:", e, flush=True)
        return {"ok": False, "text": "", "metrics": None}
    p = ev["payload"]
    return {"ok": True, "text": p["text"], "metrics": p["metrics"]}


@app.post("/end")
def end():
    send({"type": "session_end", "ts": iso_now(), "payload": {}})
    return {"ok": True}


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3100
    print("open http://localhost:%d in Chrome  (events -> %s)" % (port, SERVER), flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
