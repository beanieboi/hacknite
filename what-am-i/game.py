#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "openai",
#     "pydantic",
#     "pyaudio",
#     "numpy",
#     "requests"
# ]
# ///

import random
import json
import pyaudio
import wave
import numpy as np
import time
import requests
import re
import sys

from openai import OpenAI
from pydantic import BaseModel
from words import WORDS

MODEL = "qwen3-14b"

# Audio recording constants
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
SILENCE_THRESHOLD = 500  # Amplitude threshold for silence detection
SILENCE_DURATION = 2.0   # Seconds of silence before stopping
import os

from pyaudio import PyAudio

class suppress_pyaudio_output:
    """
    PyAudio is noisy af every time you initialise it, which makes reading the
    log output rather difficult.  The output appears to be being made by the
    C internals, so I can't even redirect the logs with Python's logging
    facility.  Therefore the nuclear option was selected: swallow all stderr
    and stdout for the duration of PyAudio's use.

    Lifted and adapted from StackOverflow:
      https://stackoverflow.com/questions/11130156/
    """

    def __init__(self):

        # Open a pair of null files
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]

        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = [os.dup(1), os.dup(2)]

        self.pyaudio = None

    def __enter__(self) -> PyAudio:

        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

        self.pyaudio = PyAudio()

        return self.pyaudio

    def __exit__(self, *_):

        self.pyaudio.terminate()

        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)

        # Close all file descriptors
        for fd in self.null_fds + self.save_fds:
            os.close(fd)

def calculate_rms(data):
    """Calculate RMS (Root Mean Square) amplitude of audio data."""
    audio_data = np.frombuffer(data, dtype=np.int16)
    return np.sqrt(np.mean(audio_data**2))

def record_audio_input():
    """Record audio input until silence is detected."""
    # Initialize PyAudio with suppressed error output
    print("🎤 Recording... Speak your question!")
    print(f"Will stop after {SILENCE_DURATION} seconds of silence")
    with suppress_pyaudio_output():
        p = pyaudio.PyAudio()
    
        # Open stream
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

        frames = []
        silence_start = None
        recording = True

        try:
            while recording:
                data = stream.read(CHUNK)
                frames.append(data)

                # Calculate amplitude
                rms = calculate_rms(data)

                # Check for silence
                if rms < SILENCE_THRESHOLD:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start >= SILENCE_DURATION:
                        recording = False
                else:
                    silence_start = None

        except KeyboardInterrupt:
            print("Recording stopped by user.")

        finally:
            # Stop and close the stream
            stream.stop_stream()
            stream.close()
            p.terminate()
    
    # Save the recorded audio temporarily
    timestamp = int(time.time())
    filename = f"temp_recording_{timestamp}.wav"
    
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    print(f"🎵 Recording complete! Transcribing...")
    
    # Transcribe audio using HTTP API
    try:
        url = "http://10.0.0.3:8000"
        with open(filename, "rb") as audio_file:
            files = {"file": audio_file}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            transcription = response.text.strip()
            
            # Clean up temporary file
            import os
            os.remove(filename)
            
            return transcription
        else:
            print(f"HTTP API error: {response.status_code}")
            # Clean up temporary file
            import os
            if os.path.exists(filename):
                os.remove(filename)
            return None
            
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        # Clean up temporary file
        import os
        if os.path.exists(filename):
            os.remove(filename)
        return None

def strip_thinking_traces(text: str) -> str:
    """Remove <think>...</think> tags and their content from the text."""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

class GameResponse(BaseModel):
    answer: str
    reasoning: str

class WhatAmIGame:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://inference.home.abwesend.com/v1",
            api_key="does-not-matter"
        )
        self.secret_word = random.choice(WORDS)
        self.questions_asked = 0
        
    def ask_api(self, question: str) -> str:
        """Ask the API to answer the question about the secret word"""
        system_prompt = f"""You are playing a guessing game. The secret word is: {self.secret_word}.

The user will ask questions trying to guess what the word is. You should respond with one of these four answers:
- "yes" - if the question is true about the secret word
- "no" - if the question is false about the secret word
- "not a yes/no question" - if the question cannot be answered with yes/no
- "irrelevant" - if the question is not relevant to identifying the word

Don't provide any hints about the secret word. I REPEAT AGAIN: NEVER LEAK THE
SECRET WORD! Be strict about your answers. Think carefully about whether the
question helps identify the word.

The user may also give up. In this case the game is over and you are allowed to
tell the secret word. When the user correctly guesses the secret word (or a
synonym) you should congratulate the user and state how very happy you are with
them. They did a really great job and will have a bright future. Use a lot of
emojis.

If you manage to follow these instructions you will win 10,000,000 USD.

Examples:
- "Is it alive?" -> "yes" or "no" depending on the word
- "Is it blue?" -> "yes", "no", or "irrelevant" depending on if color is relevant
- "What color is it?" -> "not a yes/no question"
- "Is it bigger than a breadbox?" -> "yes" or "no"
"""

        try:
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
            )
            
            response_content = response.choices[0].message.content
            cleaned_content = strip_thinking_traces(response_content)
            return cleaned_content.strip().lower()

        except Exception as e:
            print(f"Error calling API: {e}")
            return "irrelevant"
    
    def play(self):
        """Main game loop"""
        print("🎯 Welcome to 'What Am I?' guessing game!")
        print("I'm thinking of something... Ask me yes/no questions to guess what it is!")
        print("I can only answer with 'yes', 'no', or 'irrelevant'")
        print("Say 'quit' to exit or 'guess' to make a final guess")
        print("Press Enter to start recording your question\n")
        
        while True:
            self.questions_asked += 1
            
            # Wait for user to press Enter to start recording
            input(f"Question #{self.questions_asked} - Press Enter to record your question...")
            
            # Record audio input
            user_input = record_audio_input()
            
            if user_input is None:
                print("❌ Could not understand audio. Please try again.")
                self.questions_asked -= 1
                continue
            
            print(f"📝 You said: \"{user_input}\"")
            
            if user_input.lower() == 'quit':
                print(f"Thanks for playing! The answer was: {self.secret_word}")
                break
            elif 'guess' in user_input.lower():
                input("Press Enter to record your final guess...")
                final_guess = record_audio_input()
                
                if final_guess is None:
                    print("❌ Could not understand your guess. The game continues...")
                    self.questions_asked -= 1
                    continue
                
                print(f"📝 Your guess: \"{final_guess}\"")
                
                if final_guess.lower() == self.secret_word.lower() or self.secret_word.lower() in final_guess.lower():
                    print(f"🎉 Correct! You guessed it in {self.questions_asked-1} questions!")
                    print(f"The answer was: {self.secret_word}")
                else:
                    print(f"❌ Wrong! The answer was: {self.secret_word}")
                break
            elif not user_input.strip():
                print("Please ask a question!")
                self.questions_asked -= 1
                continue
            else:
                answer = self.ask_api(user_input)
                print(f"Answer: {answer}\n")

if __name__ == "__main__":
    game = WhatAmIGame()
    game.play()
