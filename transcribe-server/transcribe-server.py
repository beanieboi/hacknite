#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "fastapi",
#     "openai-whisper",
#     "python-multipart",
#     "uvicorn",
# ]
# ///

import tempfile
import os

from fastapi import FastAPI, File, UploadFile
import whisper
import uvicorn

app = FastAPI()
model = None

@app.on_event("startup")
async def startup_event():
    global model
    model = whisper.load_model("tiny")

@app.post("/")
async def transcription(file: UploadFile):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        while contents := file.file.read(1024 * 1024):
            temp_file.write(contents)
        temp_file.flush()
        file.file.close()
        result = model.transcribe(temp_file.name)["text"]
        return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
