#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "openai",
# ]
# ///

from openai import OpenAI

client = OpenAI(
    base_url="https://inference.home.abwesend.com/v1",
    api_key="does-not-matter",
)

model = "deepseek-r1-distill-qwen-14b"

completion = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
)

print(completion.choices[0].message)
