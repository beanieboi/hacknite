#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "openai-whisper",
# ]
# ///

import whisper

model = whisper.load_model("base")
result = model.transcribe("test.mp3")
print(result["text"])
