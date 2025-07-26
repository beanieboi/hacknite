#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "requests",
# ]
# ///

import requests

url = "http://10.0.0.3:8000"
files = {"file": open("test.mp3", "rb")}
response = requests.post(url, files=files)

print(response.text)
