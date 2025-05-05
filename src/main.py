from recorder import Recorder
from btn_manager import ButtonManager
from callables import CmdRegistry
from datetime import datetime
from pathlib import Path
import asyncio
import yaml
from config import Config, ButtonConfig, RecordingConfig

# Initialize

# load config
conf:dict = yaml.safe_load(open("config.yaml"))
settings = Config(
    btn_cfg = ButtonConfig(**conf.get("button_config",{})),
    rec_cfg = RecordingConfig(**conf.get("recording_config",{}))
)


# Initialize Event loop
event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(event_loop)


# Global variable to hold the recording process instance

current_filename = ""



# Initialize Recorder
recorder = Recorder(rec_cfg = settings.rec_cfg)

# Initialize Command container
cmd = CmdRegistry(recorder)


# Initialize Buttons
btn_manager = ButtonManager(button_cfg = settings.btn_cfg,
                            cmd = cmd,
                            event_loop = event_loop)


# --- Main loop ---
print(f"Press and hold button to record.")
print(f"Recordings will be saved in: {settings.rec_cfg.RECORDING_PATH}")
print("Press Ctrl+C to exit.")



# spawn sub process/thread
# load_recordings on startup
# play each recroded sound with play(filename from list)
# wait for 2 sec after each loop 
# on button press trigger event that skip track
# on button hold, stop all playback and start recording
if __name__ == "__main__":
    try:
        # Keep the script running to listen for button events
        #signal.pause()

        event_loop.run_forever()
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Exiting...")
    finally:
        # Ensure recording stops if the script exits while recording
        if (proc := recorder.get_rec_process()) is not None and proc.poll() is None:
            print("Cleaning up active recording process...")
            recorder.stop_recording()
        print("Script finished.")



