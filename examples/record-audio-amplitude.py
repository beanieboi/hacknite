#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "pyaudio",
#     "numpy",
# ]
# ///

import pyaudio
import wave
import numpy as np
import time
import threading
from collections import deque

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
SILENCE_THRESHOLD = 500  # Amplitude threshold for silence detection
SILENCE_DURATION = 2.0   # Seconds of silence before stopping


def calculate_rms(data):
    """Calculate RMS (Root Mean Square) amplitude of audio data."""
    audio_data = np.frombuffer(data, dtype=np.int16)
    return np.sqrt(np.mean(audio_data**2))


def record_audio_with_amplitude_detection():
    """Record audio until silence is detected for specified duration."""
    
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    
    # Open stream
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    print("Recording... Speak now!")
    print(f"Will stop after {SILENCE_DURATION} seconds of silence (amplitude < {SILENCE_THRESHOLD})")
    
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
                    print("Silence detected...")
                elif time.time() - silence_start >= SILENCE_DURATION:
                    print("Stopping recording due to prolonged silence.")
                    recording = False
            else:
                if silence_start is not None:
                    print("Sound detected, continuing recording...")
                silence_start = None
            
            # Print current amplitude level
            print(f"Amplitude: {rms:6.0f} {'(SILENCE)' if rms < SILENCE_THRESHOLD else ''}", end='\r')
    
    except KeyboardInterrupt:
        print("\nRecording stopped by user.")
    
    finally:
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        p.terminate()
    
    # Save the recorded audio
    timestamp = int(time.time())
    filename = f"recording_{timestamp}.wav"
    
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    print(f"\nRecording saved as: {filename}")
    print(f"Duration: {len(frames) * CHUNK / RATE:.2f} seconds")


if __name__ == "__main__":
    try:
        record_audio_with_amplitude_detection()
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure your system has a working microphone and audio drivers.")
