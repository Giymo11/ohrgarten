#!/usr/bin/env python3
from gpiozero import Button
from signal import pause
from datetime import datetime
import time, signal, subprocess, os
from pathlib import Path

BUTTON_PIN = 17
RST_BUTTON_PIN = 27

RECORDING_PATH = "/home/giymo11/dev/ohrgarten/recordings"
SFX_PATH = "/home/giymo11/dev/ohrgarten/sfx"
BEEP_FILE = SFX_PATH + "/beep.wav"

ARECORD_CMD = [
    "arecord",
    "-f", "cd",       # Record in CD quality (16-bit little endian, 44100 Hz, Stereo)
    "-t", "wav",      # Save as WAV file type
    "-D", "plughw:2,0",  # find from 'arecord -l'
]
APLAY_CMD = ["aplay", "-D", "plughw:2,0"] # Use default output device

# Global variable to hold the recording process instance
recording_process = None
current_filename = ""
recorded_files = []

os.makedirs(RECORDING_PATH, exist_ok=True)

# Use the BCM pin number (GPIO 17, physical pin 11)
button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.1)

rst_button = Button(RST_BUTTON_PIN, pull_up=True, bounce_time=0.1)

def load_recordings():
    """Scans the RECORDING_PATH for .wav files and populates the recorded_files list."""
    global recorded_files
    recorded_files = [] 

    path = Path(RECORDING_PATH)
    print(f"Scanning for recordings in: {path}...")
    if not path.is_dir():
        print(f"Warning: Recording directory {path} does not exist. Creating.")
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Error creating directory {path}: {e}")
            return # Cannot proceed without the directory

    count = 0
    for item in path.iterdir():
        if item.is_file() and item.suffix.lower() == ".wav":
            recorded_files.append(item) 
            count += 1
    recorded_files.sort() # Sort alphabetically/chronologically if names allow
    print(f"Found {count} existing recordings.")
    # print(f"Loaded file list: {[f.name for f in recorded_files]}")


def reset_recordings():
    global recorded_files
    
    print("Clearing the in-memory list of tracked recordings.")
    recorded_files.clear() 
    
    path = Path(RECORDING_PATH)
    for item in path.iterdir():
        try:
            if item.is_file() and item.suffix.lower() == ".wav":
                item.unlink() # Delete the file
        except PermissionError:
            print(f"Failed (Permission denied). Check permissions for {file_path}")
            failure_count += 1
        except OSError as e:
             print(f"Failed (OS Error: {e}).") # Catch other potential file system errors
             failure_count += 1
        except Exception as e:
            print(f"Failed (Unexpected Error: {e}).")
            failure_count += 1
    

def start_recording():
    """Starts the arecord process."""
    global recording_process
    global current_filename

    if recording_process is None and current_filename == '': 
        try:
            # Generate a unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_filename = os.path.join(RECORDING_PATH, f"rec_{timestamp}.wav")
            full_command = ARECORD_CMD + [current_filename]

            print(f"Starting recording to: {current_filename}")
            print(f"Command: {' '.join(full_command)}")

            # Start arecord as a background process using Popen
            recording_process = subprocess.Popen(full_command, stderr=subprocess.PIPE)
            print(f"Recording started (PID: {recording_process.pid})... Press and hold button.")

        except FileNotFoundError:
             print("Error: 'arecord' command not found. Is alsa-utils installed?")
             recording_process = None 
        except Exception as e:
            print(f"Error starting recording process: {e}")
            recording_process = None 
    else:
        print("Already recording.") 

def stop_recording():
    """Stops the arecord process."""
    global recording_process
    global current_filename

    if recording_process is not None:
        print(f"Stopping recording (PID: {recording_process.pid})...")
        try:
            # Send SIGTERM signal first (allows arecord to potentially clean up)
            recording_process.terminate()
            time.sleep(0.2)
            
            if recording_process.poll() is None: # Check if process is still running
                 print("Process did not terminate, sending SIGKILL.")
                 recording_process.kill()

            # Wait for the process to actually finish and retrieve output/errors
            stdout, stderr = recording_process.communicate(timeout=5) 

            print(f"Recording stopped. File saved: {current_filename}")
            if stderr:
                print(f"Recording process stderr:\n{stderr.decode('utf-8', errors='ignore')}")

        except subprocess.TimeoutExpired:
            print("Error: Timeout waiting for arecord process to terminate after signaling.")
            # Force kill if timeout occurred during communicate()
            recording_process.kill()
            recording_process.wait() # Ensure it's cleaned up
            print("Process killed due to timeout.")
        except Exception as e:
            print(f"Error stopping recording process: {e}")
            # Ensure we try to kill it if an error occurred during termination steps
            if recording_process.poll() is None:
                recording_process.kill()
                recording_process.wait()


        # Reset the global variable
        recording_process = None
        
        play_sound(BEEP_FILE)
        play_sound(current_filename)
        current_filename = ""
    else:
        print("Not currently recording.")


def play_sound(filename):
    # if not BEEP_PATH.is_file():
    #     print(f"Warning: Beep file not found at {BEEP_PATH}")
    #     return

    print(f"Playing {filename}...")
    try:
        # Run aplay and wait for it to complete. Capture output to hide it unless error.
        cmd = APLAY_CMD + [filename]
        subprocess.run(cmd, check=True, capture_output=True, timeout=5) # Check=True raises error on fail
        print("Beep finished.")
    except FileNotFoundError:
         print("Error: 'aplay' command not found. Is alsa-utils installed?")
    except subprocess.CalledProcessError as e:
        print(f"Error playing beep using aplay: {e}")
        print(f"Stderr: {e.stderr.decode('utf-8', errors='ignore')}")
    except subprocess.TimeoutExpired:
        print("Error: Timeout playing beep sound.")
    except Exception as e:
        print(f"An unexpected error occurred during beep playback: {e}")




button.when_pressed = start_recording
button.when_released = stop_recording
rst_button.when_pressed = reset_recordings

# --- Main loop ---
print(f"Press and hold button to record.")
print(f"Recordings will be saved in: {RECORDING_PATH}")
print("Press Ctrl+C to exit.")

try:
    # Keep the script running to listen for button events
    signal.pause()
except KeyboardInterrupt:
    print("\nCtrl+C detected. Exiting...")
finally:
    # Ensure recording stops if the script exits while recording
    if recording_process is not None and recording_process.poll() is None:
        print("Cleaning up active recording process...")
        stop_recording()
    print("Script finished.")

