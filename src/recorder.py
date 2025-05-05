from config import RecordingConfig
from pathlib import Path
import os
from datetime import datetime
import time, signal, subprocess, os


class Recorder:
    
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


    def get_rec_process(self) -> subprocess.Popen | None:
        return self.recording_process
    
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
        """Starts the arecord process."""
        
        if self.recording_process is None: 
            try:
                # Generate a unique filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.current_filename = os.path.join(self.rec_path, f"rec_{timestamp}.wav")
                full_command = self.rec_cfg.ARECORD_CMD + [self.current_filename]

                print(f"Starting recording to: {self.current_filename}")
                print(f"Command: {' '.join(full_command)}")

                # Start arecord as a background process using Popen
                self.recording_process = subprocess.Popen(full_command, stderr=subprocess.PIPE)
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
                self.recording_process.terminate()
                time.sleep(0.2)
                
                if self.recording_process.poll() is None: # Check if process is still running
                    print("Process did not terminate, sending SIGKILL.")
                    self.recording_process.kill()

                # Wait for the process to actually finish and retrieve output/errors
                stdout, stderr = self.recording_process.communicate(timeout=5) 

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

            self.play_sound(self.BEEP)
            self.play_sound(self.current_filename)

        else:
            print("Not currently recording.")


    #def supress_background_noise(self, filename):

        # wf = wave.open(filename, "rb")
        # assert wf.getframerate() in (8000, 16000, 32000, 48000)
        # assert wf.getnchannels() == 1 and wf.getsampwidth() == 2

        # vad = webrtcvad.Vad(2)
        # sr = wf.getframerate()
        # frame_ms      = 20
        # frame_samples = int(sr * frame_ms / 1000)
        # frame_bytes   = frame_samples * wf.getsampwidth()

        # out = wave.open(filename + '1.wav', "wb")
        # out.setparams(wf.getparams())

        # while True:
        #     data = wf.readframes(frame_samples)
        #     if len(data) < frame_bytes:
        #         break
        #     if vad.is_speech(data, sr):
        #         out.writeframes(data)

        # wf.close()
        # out.close()


    def play_sound(self, filename):

        print(f"Playing {filename}...")
        try:
            # Run aplay and wait for it to complete. Capture output to hide it unless error.
            cmd = self.rec_cfg.APLAY_CMD + [filename]
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



    def skip_recording(self):
        print(f"Skipping recording {self.current_filename}")
