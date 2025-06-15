from config import RecordingConfig
from pathlib import Path
import os
from datetime import datetime
import time, signal, subprocess, os
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter
from typing import TYPE_CHECKING
import threading
import asyncio

if TYPE_CHECKING:
    from cmd_typing import CmdTyping



class Recorder:

    recording_start = 0
    
    def __init__(self, rec_cfg: RecordingConfig):
        # Initialize folders
        self.rec_cfg = rec_cfg
        try:
            os.makedirs(rec_cfg.RECORDING_PATH, exist_ok=True)
        except OSError as err:
            print(f"Error creating directory at {self.rec_path}: {err}")
            raise Exception

        self.rec_path = rec_cfg.RECORDING_PATH
        self.BEEP = rec_cfg.SFX_PATH + "/" +  rec_cfg.BEEP_FILE
        self.recording_process: subprocess.Popen | None = None
        self.buffer = self._load_recordings()
        self.current_filename = ''


    def inject_cmd(self, cmd:"CmdTyping"):
        self.cmd = cmd

    def get_rec_buffer(self) -> list:
        return self.buffer

    def get_rec_process(self) -> subprocess.Popen | None:
        return self.recording_process
    
    def get_current_recording(self) -> str:
        return self.current_filename

    def _load_recordings(self) -> list:
        """Scans the RECORDING_PATH for .wav files and populates the recorded_files list."""
        recorded_files = [] 
        print(f"Scanning for recordings in: {self.rec_path}...")

        path = Path(self.rec_path)
        count = 0

        for item in path.iterdir():
            if item.is_file() and item.suffix.lower() == ".wav":
                recorded_files.append(item) 
                count += 1

        recorded_files.sort() # Sort alphabetically/chronologically if names allow
        print(f"Found {count} existing recordings.")
        return recorded_files

    def delete_recording(self, filename = None):
        if filename is None:
            filename = self.current_filename

        if os.path.exists(filename):
            os.remove(filename)
            print(f"Deleted file: {filename}")
        else:
            print(f"File not exist: {filename}")

    def reset_recordings(self):
        
        print("Clearing the in-memory list of tracked recordings.")

        
        path = Path(self.rec_path)
        failure_count = 0
        for item in path.iterdir():
            try:
                if item.is_file() and item.suffix.lower() == ".wav":
                    item.unlink() # Delete the file
            except PermissionError:
                print(f"Failed (Permission denied). Check permissions for {self.rec_path}")
                failure_count += 1
            except OSError as e:
                print(f"Failed (OS Error: {e}).") # Catch other potential file system errors
                failure_count += 1
            except Exception as e:
                print(f"Failed (Unexpected Error: {e}).")
                failure_count += 1
            finally:
                if failure_count > 0:
                    raise Exception

        self.buffer.clear()
        

    def start_recording(self):
        print("Started rec func")
        """Starts the arecord process."""
        self.cmd.player.pause()
        #self.cmd.play_sound(self.BEEP)
        if self.recording_process is None: 
            self.cmd.led.recording_led_on()


            try:
                # Generate a unique filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.current_filename = os.path.join(self.rec_path, f"rec_{timestamp}.wav")
                full_command = self.rec_cfg.ARECORD_CMD + [self.current_filename]

                print(f"Starting recording to: {self.current_filename}")
                print(f"Command: {' '.join(full_command)}")

                # Start arecord as a background process using Popen
                # Duration of recording limited to config defined arecord cmd duration
                self.recording_process = subprocess.Popen(full_command, stderr=subprocess.PIPE)
                Recorder.recording_start = time.time()
                print(f"Recording started (PID: {self.recording_process.pid})... Press and hold button.")

            except FileNotFoundError:
                print("Error: 'arecord' command not found. Is alsa-utils installed?")
                self.recording_process = None 
            except Exception as e:
                print(f"Error starting recording process: {e}")
                self.recording_process = None 
        else:
            print("Already recording.") 


    def stop_recording(self):
        """Stops the arecord process."""

        if self.recording_process is not None:
            print(f"Stopping recording (PID: {self.recording_process.pid})...")
            try:
                # Send SIGTERM signal first (allows arecord to potentially clean up)
                rec_duration = time.time() - Recorder.recording_start
                self.recording_process.terminate()
                time.sleep(0.2)
                
                if self.recording_process.poll() is None: # Check if process is still running
                    print("Process did not terminate, sending SIGKILL.")
                    self.recording_process.kill()

                # Wait for the process to actually finish and retrieve output/errors
                stdout, stderr = self.recording_process.communicate(timeout=2) 

                print(f"Recording stopped. File saved: {self.current_filename}")
                if stderr:
                    print(f"Recording process stderr:\n{stderr.decode('utf-8', errors='ignore')}")

            except subprocess.TimeoutExpired:
                print("Error: Timeout waiting for arecord process to terminate after signaling.")
                # Force kill if timeout occurred during communicate()
                self.recording_process.kill()
                self.recording_process.wait() # Ensure it's cleaned up
                print("Process killed due to timeout.")
            except Exception as e:
                print(f"Error stopping recording process: {e}")
                # Ensure we try to kill it if an error occurred during termination steps
                if self.recording_process.poll() is None:
                    self.recording_process.kill()
                    self.recording_process.wait()


            # Reset the global variable
            self.recording_process = None
            
            #self.supress_background_noise(self.current_filename)

            if self.check_len(duration = rec_duration, threshold = 1.5):
                print("Include recording")
                self.apply_filter(self.current_filename)

                print("Start confrimation phase")
                self.cmd.led.led_off()
                
                self.confirm_routine()
                #self.cmd.start_confirmation(self.current_filename)


        else:
            print("Not currently recording.")

        self.cmd.player.resume()
        #self.cmd.start()

    def confirm_routine(self):
        self.cmd.button.button_await_confirm(True)

        thread = self.cmd.player.start_confirmation(self.current_filename)

        def _watch():
            thread.join()
            self.cmd.button.button_await_confirm(False)
            self.cmd.player.resume()

        threading.Thread(target=_watch, daemon=True).start()
    

    def check_len(self, duration, threshold = 3.0) -> bool:


        print(duration)
        if duration < threshold:
            
            # do not include recording, most likely mistake
            return False
        # include recording
        return True

    def apply_filter(self, filename):
        rate, data = wavfile.read(filename)
        if data.ndim == 1:
            filtered = self.lowpass(data, cutoff_freq=3000, sample_rate=rate)
        else:
            filtered = np.array([self.lowpass(channel, 3000, rate) for channel in data.T]).T

        filtered = np.clip(filtered, -32768, 32767).astype(np.int16)
        wavfile.write(filename, rate, filtered)


    def lowpass(self, data, cutoff_freq, sample_rate, order=5):
        nyquist = 0.5 * sample_rate
        norm_cutoff = cutoff_freq / nyquist
        b, a = butter(order, norm_cutoff, btype='low', analog=False)
        return lfilter(b, a, data)


