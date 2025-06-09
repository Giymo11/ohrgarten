from dataclasses import dataclass
from typing import List, Final

@dataclass
class ButtonConfig:
    BUTTON_PIN: Final[int]
    RST_BUTTON_PIN: Final[int]

@dataclass
class RecordingConfig:
    RECORDING_PATH: Final[str]
    SFX_PATH: Final[str]
    BEEP_FILE: Final[str]
    ARECORD_CMD: Final[List[str]]


@dataclass
class PlayerConfig:
    APLAY_CMD:  Final[List[str]]

@dataclass
class LedConfig:
    DATA_PIN: Final[str]
    PIXEL_NUM: Final[int]

# wrap everything under 1 config
@dataclass
class Config:
    btn_cfg: ButtonConfig
    rec_cfg: RecordingConfig
    ply_cfg: PlayerConfig
    led_cfg: LedConfig
