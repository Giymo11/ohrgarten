from config import PlayerConfig
from pathlib import Path
import os
from datetime import datetime
import time, signal, subprocess, os
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cmd_typing import CmdTyping



class Player:

    def __init__(self, ply_cfg: PlayerConfig):
        self.APLAY_CMD = ply_cfg.APLAY_CMD
        self.buffer: list
        self._idx = 0
        self._stop_event  = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._skip_event = threading.Event()
        self._lock = threading.Lock()
        self.playing_proc: subprocess.Popen | None = None


    def inject_cmd(self, cmd:"CmdTyping"):
        self.cmd = cmd
        # start any cmd that are now possible as initialization step
        self.buffer = self.cmd.get_rec_buffer()


    # plays sound until finished 
    # useful for short sfx
    def play_sound(self, filename):
        
        # only for beep sound usecase
        # terminate all other playback processes in order to play beep.
        if self.playing_proc:
            self.playing_proc.terminate()
        time.sleep(0.1)

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

    # plays soun
    def _play_sound_non_blocking(self, filename) -> subprocess.Popen:
            # start playback
        proc = subprocess.Popen(
            self.APLAY_CMD + [filename],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return proc
    
    def pause_player(self):
        # terminate currently playing process
        self.skip_player()
        # pauses playback loop
        self._pause_event.clear()
        print(f"pause player")

    # unpauses playback loop
    def resume_player(self):
        self._pause_event.set()
        print(f"resume player")

    # completely kills the loop and thus the thread
    def stop_player(self):
        self._stop_event.set()
        print(f"terminating playback")

    # terminate currently playing process, thus skipping to next loop
    def skip_player(self):
        self._skip_event.set()
        print(f"invoke button skip")
        

    # gpt was here
    def play_forever(self):
        while not self._stop_event.is_set():
            # waits until  resume_player has been called by setting _pause_event.set()
            self._pause_event.wait()
            if not self.buffer:
                time.sleep(0.1)
                continue
                
            # TODO!: fix random playback after pressing skip
            # pick next index
            with self._lock:
                current = self._idx
                self._idx = (self._idx + 1) % len(self.buffer)
            filename = self.buffer[current]

            self.playing_proc = self._play_sound_non_blocking(filename)

            # watch for skip or natural end
            while self.playing_proc.poll() is None:
                if self._skip_event.is_set() and self.playing_proc:
                    self.playing_proc.terminate()
                    self.playing_proc = None
                    self._skip_event.clear()
                    break
                time.sleep(0.05)
