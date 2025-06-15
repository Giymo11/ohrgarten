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
        self.confirmation_phase = False


    def inject_cmd(self, cmd:"CmdTyping"):
        self.cmd = cmd
        # start any cmd that are now possible as initialization step
        self.buffer = self.cmd.get_rec_buffer()


    # extending recording buffer moved here to simplify threading lock mechanism without needing to expose the _lock to cmd
    def extend_buffer(self, recording=None):
        if not recording:
            recording = self.cmd.get_current_recording()
        with self._lock:
            insert_pos = (self._idx + 1) % (len(self.buffer) + 1)
            self.buffer.insert(insert_pos, recording)

    # plays sound until finished 
    # useful for short sfx
    def play_sound(self, filename):
        timeout = 20
        # only for beep sound usecase
        # terminate all other playback processes in order to play beep.
        if self.playing_proc:
            self.playing_proc.terminate()
        time.sleep(0.1)

        print(f"Playing {filename}...")
        try:
            # Run aplay and wait for it to complete. Capture output to hide it unless error.
            cmd = self.APLAY_CMD + [filename]
            subprocess.run(cmd, check=True, capture_output=True, timeout=timeout) # Check=True raises error on fail
            print("Play Finished.")
        except FileNotFoundError:
            print("Error: 'aplay' command not found. Is alsa-utils installed?")
        except subprocess.CalledProcessError as e:
            print(f"Error playing beep using aplay: {e}")
            print(f"Stderr: {e.stderr.decode('utf-8', errors='ignore')}")
        except subprocess.TimeoutExpired:
            print(f"Recording reached {timeout} sec timeout.")
        except Exception as e:
            print(f"An unexpected error occurred during beep playback: {e}")

    # plays soun
    def _play_sound_non_blocking(self, filename) -> subprocess.Popen:
            # start playback
        print(f"Playing recording at index {self._idx}")
        proc = subprocess.Popen(
            self.APLAY_CMD + [filename],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return proc
    
    def _terminate_current_playback(self):
        proc = self.playing_proc

        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except Exception:
                pass

    def pause_player(self):
        # terminate currently playing process
        #self.skip_player()
        self._terminate_current_playback()
        # pauses playback loop
        self._pause_event.clear()
        print(f"pause player")

    # unpauses playback loop
    def resume_player(self):
        #! experimental
        #! self._terminate_current_playback()
        self._pause_event.set()
        print(f"resume player")

    # completely kills the loop and thus the thread
    def stop_player(self):
        self._terminate_current_playback()
        self._stop_event.set()
        print(f"terminating playback")

    # terminate currently playing process, thus skipping to next loop
    def skip_player(self):
        with self._lock:
            self._skip_event.set()
            self._idx = (self._idx + 1) % len(self.buffer)

        self._terminate_current_playback()

        print("invoke button skip")

    def playback_hold_confirm(self):
        self.pause_player()

        self._play_sound_non_blocking('sfx/rising_meter.wav')

# loop filename and instruction 
    def _loop_recording_and_instruction(self, filename):
        print("Loop confirmation phase")
        loop_buffer = [filename, 'sfx/beep.wav']
        index = 0
        self.resume_player()
        while not self._stop_event.is_set():
            self._pause_event.wait()
            file = loop_buffer[index]
            self.playing_proc = self._play_sound_non_blocking(file)
            while self.playing_proc and self.playing_proc.poll() is None:
                time.sleep(0.1)

            self.playing_proc = None

            index = (index + 1) % 2

        self._stop_event.clear()
        self.confirmation_phase = False
        self.cmd.button_await_confirm(False)

    def start_confirmation(self, filename):
        self._terminate_current_playback()
        self.confirmation_phase = True
        threading.Thread(target=self._loop_recording_and_instruction, args = (filename,), daemon= True).start()
        #self._loop_recording_and_instruction(filename)

    
    def play_forever(self):
        while not self._stop_event.is_set():
            # waits until resume_player has been called by setting _pause_event.set()
            self._pause_event.wait()
            if self.confirmation_phase:
                time.sleep(0.5)
                continue
            if not self.buffer:
                time.sleep(0.1)
                continue
                
            # TODO!: fix random playback after pressing skip
            # pick next index
            with self._lock:
                filename = self.buffer[self._idx]

            self.playing_proc = self._play_sound_non_blocking(filename)

            # None == Process still running
            while self.playing_proc and self.playing_proc.poll() is None:
                # when skipped triggered, then don't need to wait for process to terminate, as it is already terminated by skip
                if self._skip_event.is_set():
                    break
                time.sleep(0.1)

            self.playing_proc = None

            # advance index only if not already advanced by skip
            with self._lock:
                if self._skip_event.is_set():
                    self._skip_event.clear()
                    continue
                self._idx = (self._idx + 1) % len(self.buffer)
           
           