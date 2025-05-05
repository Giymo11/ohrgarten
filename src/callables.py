from typing import Protocol, Callable
from recorder import Recorder

# Just for pylance (highlighting)
class CmdTyping(Protocol):

    def reset_recordings(self) -> None: ...
    def start_recording(self) -> None: ...
    def skip_recording(self) -> None: ...
    def stop_recording(self) -> None: ...

class CmdRegistry:
    def __init__(self, recorder:Recorder):
        self.reset_recordings = recorder.reset_recordings
        self.start_recording = recorder.start_recording
        self.skip_recording = recorder.skip_recording
        self.stop_recording = recorder.stop_recording

    
