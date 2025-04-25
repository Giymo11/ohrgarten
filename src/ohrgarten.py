#!/usr/bin/env python3
from gpiozero import Button
from signal import pause
import time, signal, subprocess, os

BUTTON_PIN = 17
ARECORD_CMD = [
    "arecord",
    "-D", "plughw:2,0 ",  # find from 'arecord -l'
    "-f", "cd",       # Record in CD quality (16-bit little endian, 44100 Hz, Stereo)
    "-t", "wav"       # Save as WAV file type
]

# Global variable to hold the recording process instance
recording_process = None
current_filename = ""

# Use the BCM pin number (GPIO 17, physical pin 11)
button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.1)

def button_pressed():
    print("Button Pressed!")

def button_released():
    print("Button Released!")

print("Button script running. Press Ctrl+C to exit.")

# Assign the functions to the button events
button.when_pressed = button_pressed
button.when_released = button_released

# Keep the script running to listen for events
pause()

# Note: gpiozero handles cleanup automatically on normal exit.
