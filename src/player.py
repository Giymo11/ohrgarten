from config import PlayerConfig
from pathlib import Path
import os
from datetime import datetime
import time, signal, subprocess, os


class Player:

    def __init__(self, ply_cfg: PlayerConfig):
        self.APLAY_CMD = ply_cfg.APLAY_CMD


    def play_sound(self, filename):

        print(f"Playing {filename}...")
        try:
            # Run aplay and wait for it to complete. Capture output to hide it unless error.
            cmd = self.APLAY_CMD + [filename]
            subprocess.run(cmd, check=True, capture_output=True, timeout=5) # Check=True raises error on fail
            print("Play Finished.")
        except FileNotFoundError:
            print("Error: 'aplay' command not found. Is alsa-utils installed?")
        except subprocess.CalledProcessError as e:
            print(f"Error playing beep using aplay: {e}")
            print(f"Stderr: {e.stderr.decode('utf-8', errors='ignore')}")
        except subprocess.TimeoutExpired:
            print("Error: Timeout playing beep sound.")
        except Exception as e:
            print(f"An unexpected error occurred during beep playback: {e}")

