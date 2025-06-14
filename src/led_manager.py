import board
import neopixel
import asyncio
from config import LedConfig

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cmd_typing import CmdTyping

RED = (20, 0, 0)
GREEN = (0, 20, 0)
BLUE = (0, 0, 20)
OFF = (0, 0, 0)

class LedManager:
    def __init__(self, led_cfg: LedConfig, event_loop):
        
        self.led_pin = led_cfg.DATA_PIN
        self.led_num = led_cfg.PIXEL_NUM

        if self.led_pin or self.led_pin in ["D10", "D12", "D18", "D20"]:
            self.led:neopixel.NeoPixel = neopixel.NeoPixel(getattr(board, self.led_pin), led_cfg.PIXEL_NUM)

        else:
            self.led = None
            print("Led not configured.")
        
        self.event_loop: asyncio.AbstractEventLoop = event_loop
        self.event_loop.create_task(self.startup_sequence())

    async def startup_sequence(self):
        if not self.led:
            return

        # Blink red 3 times within 2 seconds (approx 0.33s on/off)
        for _ in range(3):
            self.led[0] = (30, 0, 0)  # Red
            await asyncio.sleep(0.33)
            self.led[0] = (0, 0, 0)  # Off
            await asyncio.sleep(0.33)

        # Green for 1 second
        self.led[0] = (0, 30, 0)  # Green
        await asyncio.sleep(1)

        # Turn off
        self.led[0] = (0, 0, 0)

    def inject_cmd(self, cmd:"CmdTyping"):
        self.cmd = cmd
    
    def recording_led_on(self):
        if not self.led:
            return
        self.led[0] = RED
        print("LED RED")

    def replay_led_on(self):
        if not self.led:
            return
        self.led[0] = GREEN
    
    def instruction_led_on(self):
        if not self.led:
            return
        self.led[0] = BLUE
    
    def led_off(self):
        if not self.led:
            return
        self.led[0] = OFF

    def shutdown_neopixel(self):
        self.led.fill((0, 0, 0))
        self.led.show()
        print(f"Freeing up LED gpio pin {self.led_pin}")
        del self.led
