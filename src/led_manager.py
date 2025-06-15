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
    
    def start_delayed_led_off(self, duration: float):
        task = self.event_loop.create_task(self.led_off_after_duration(duration))
        return task

    def start_deleted_led_seq(self, duration: float):
        task = self.event_loop.create_task(self.deleted_led(duration))
        return task

    def start_confirm_led_seq(self, duration: float):
        task = self.event_loop.create_task(self.confirm_led(duration))
        return task

    def stop_led_task(self, task: asyncio.Task):
        if task and not task.done():
            task.cancel()
            task = None


    async def led_rising(self, color, steps, interval):
        r_scale, g_scale, b_scale = color
        for i in range(steps + 1):
            r = int(r_scale * i)
            g = int(g_scale * i)
            b = int(b_scale * i)
            self.led[0] = (r, g, b)
            await asyncio.sleep(interval)

    async def confirm_led(self, duration):
        if not self.led:
            return
        color = (0, 1, 0)
        steps = 30
        interval = duration / steps
        try:
            await self.led_rising(color=color, steps = steps, interval=interval)
        except asyncio.CancelledError:
            self.led[0] = OFF
    
    async def led_falling(self, color, steps, interval):
        r_start, g_start, b_start = color
        for i in range(steps + 1):
            r = int(r_start * (1 - i / steps))
            g = int(g_start * (1 - i / steps))
            b = int(b_start * (1 - i / steps))
            self.led[0] = (r, g, b)
            await asyncio.sleep(interval)

    async def deleted_led(self, duration):
        if not self.led:
            return
        color = (20, 0, 0)
        steps = 20
        interval = duration/ steps
        try:
            await self.led_falling(color=color, steps = steps, interval=interval)
        except asyncio.CancelledError:
            self.led[0] = OFF

    async def led_off_after_duration(self, duration):
        if not self.led:
            return
        await asyncio.sleep(duration)
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
