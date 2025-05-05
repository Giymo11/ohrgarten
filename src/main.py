from recorder import Recorder
from player import Player
from btn_manager import ButtonManager
#from callables import CmdTyping
from datetime import datetime
from pathlib import Path
import asyncio
import yaml
from config import Config, ButtonConfig, RecordingConfig, PlayerConfig

# Initialize

# load config
conf:dict = yaml.safe_load(open("config.yaml"))
settings = Config(
    btn_cfg = ButtonConfig(**conf.get("button_config",{})),
    rec_cfg = RecordingConfig(**conf.get("recorder_config",{})),
    ply_cfg = PlayerConfig(**conf.get("player_config", {}))
)


# Initialize Event loop
event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(event_loop)



# Initialize Recorder
recorder = Recorder(rec_cfg = settings.rec_cfg)

# Initialize Player
player = Player(ply_cfg = settings.ply_cfg)

# Initialize Buttons
btn_manager = ButtonManager(button_cfg = settings.btn_cfg,
                            event_loop = event_loop)

class CmdRegistry:
    def __init__(self,
                 recorder: Recorder,
                 player:   Player,
                 buttons:  ButtonManager):
        self.reset_recordings = recorder.reset_recordings
        self.start_recording = recorder.start_recording
        self.skip_recording = recorder.skip_recording
        self.stop_recording = recorder.stop_recording
        self.play_sound = player.play_sound

        recorder.inject_cmd(self)
        buttons.inject_cmd(self)


# Initialize Command container allowing cross instance access of selected methods without importing whole classes
cmd = CmdRegistry(recorder, player, btn_manager)

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



