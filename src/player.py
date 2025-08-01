from config import PlayerConfig
from pathlib import Path
import os
from datetime import datetime
import time, signal, subprocess, os
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cmd_typing import CmdTyping

# every 7th playback is the original creators question defined by ply_cfg.QUESTION
nth_question_repeat = 7

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
        #self.playing_proc: subprocess.Popen | None = None
        self.confirmation_phase = False
        self._stop_confirmation = threading.Event()
        self.question = ply_cfg.VOICE_PATH + '/' + ply_cfg.QUESTION 



    def inject_cmd(self, cmd:"CmdTyping"):
        self.cmd = cmd
        # start any cmd that are now possible as initialization step
        self.buffer = self.cmd.recorder.get_rec_buffer()


    # extending recording buffer moved here to simplify threading lock mechanism without needing to expose the _lock to cmd
    def extend_buffer(self, recording=None):
        if not recording:
            recording = self.cmd.recorder.get_current_recording()
        with self._lock:
            insert_pos = (self._idx + 1) % (len(self.buffer) + 1)
            self.buffer.insert(insert_pos, recording)

    # plays sound until finished 
    # useful for short sfx
    def play_sound(self, filename):
        timeout = 20
        # only for beep sound usecase
        # terminate all other playback processes in order to play beep.
        # if self.playing_proc:
        #     self.playing_proc.terminate()
        # time.sleep(0.1)

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
    

    def terminate_current_playback(self, proc: subprocess.Popen):
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except Exception as err:
                print(f"Error during terminating playback: {str(err)}")

    def pause(self):
        # terminate currently playing process
        #self.skip_player()
        #self._terminate_current_playback()
        # pauses playback loop
        self._pause_event.clear()
        print(f"pause player")

    # unpauses playback loop
    def resume(self):
        #! experimental
        #self.terminate_current_playback()
        self._pause_event.set()
        print(f"resume player")

    # completely kills the loop and thus the thread
    def stop(self):
        self.pause()
        self._stop_event.set()
        print(f"terminating playback")

    def stop_confirmation_loop(self):
        self.pause()
        self._stop_confirmation.set()
        print(f"terminating confirmation")

    # terminate currently playing process, thus skipping to next loop
    def skip(self):
        if self.confirmation_phase:
            return
        with self._lock:
            self._skip_event.set()
            self._idx = (self._idx + 1) % len(self.buffer)

        #self._terminate_current_playback()

        print("invoke button skip")

    def playback_hold_confirm(self):
        self.pause()
        time.sleep(0.2)
        print("Playing sfx/rising.wav")
        proc = self._play_sound_non_blocking('sfx/rising.wav')

        return proc
    
    def playback_delete(self):
        self.pause()
        time.sleep(0.2)
        print("Playing sfx/delete.wav")
        proc = self._play_sound_non_blocking('sfx/delete.wav')

        return proc
    
    # loop confirmation after recording
    def _loop_recording_and_instruction(self, filename):
        print("Loop confirmation phase")
        loop_buffer = [filename, 'voice/save.wav']
        index = 0
        self.resume()
        while not self._stop_confirmation.is_set():
            self._pause_event.wait()
            file = loop_buffer[index]
            if index:
                self.cmd.led.instruction_led_on()
            else:
                self.cmd.led.replay_led_on()

            proc = self._play_sound_non_blocking(file)

            while True:

                if proc is None or proc.poll() is not None:
                    break

                if not self._pause_event.is_set() or self._stop_confirmation.is_set():
                    self.terminate_current_playback(proc)
                    break
                time.sleep(.1)


            index = (index + 1) % 2
            self.cmd.led.led_off()
            for _ in range(10):
                if self._stop_confirmation.is_set():
                    break
                time.sleep(0.1)

        self._stop_confirmation.clear()
        self.confirmation_phase = False
        self.cmd.button.button_await_confirm(False)

    def start_confirmation(self, filename):

        if self.confirmation_phase:
            return

        self.confirmation_phase = True
        thread = threading.Thread(target=self._loop_recording_and_instruction, args = (filename,), daemon= True)
        thread.start()
        return thread
        #self._loop_recording_and_instruction(filename)

    
    def play_forever(self):
        question_counter = 0
        while not self._stop_event.is_set():

            for _ in range(10):
                if self._skip_event.is_set():
                    break
                time.sleep(0.1)


            # waits until resume_player has been called by setting _pause_event.set()
            self._pause_event.wait()
            if self.confirmation_phase:
                time.sleep(0.5)
                continue

            # if not self.buffer:
            #     time.sleep(0.1)
            #     continue

            # play question or recroding
            
            if not self.buffer or question_counter % nth_question_repeat == 0:
                filename = self.question
                led_color = self.cmd.led.instruction_led_on()
            else:
                with self._lock:
                    filename = self.buffer[self._idx]
                    led_color = self.cmd.led.replay_led_on()
                
            proc = self._play_sound_non_blocking(filename)

            while True:
                if proc is None or proc.poll() is not None:
                    break
                if self._skip_event.is_set() or not self._pause_event.is_set():
                    self.terminate_current_playback(proc=proc)
                    break
                time.sleep(0.1)

            if self._pause_event.is_set():
                self.cmd.led.led_off()
            question_counter = question_counter + 1

            with self._lock:
                if self._skip_event.is_set():
                    self._skip_event.clear()
                    continue
                # do not advance index if the question was repeated
                if filename == self.question:
                    continue
                self._idx = (self._idx + 1) % len(self.buffer)
            
            
           
           