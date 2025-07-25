from config import ButtonConfig
from gpiozero import Button
import asyncio
from asyncio import Event
from concurrent.futures import Future
from typing import TYPE_CHECKING
import time

if TYPE_CHECKING:
    from cmd_typing import CmdTyping

class ButtonManager:

    def __init__(self, button_cfg: ButtonConfig, event_loop):
        


        self.button: Button = self._initialize_button(button_cfg.BUTTON_PIN)
        self.reset_button: Button = self._initialize_button(button_cfg.RST_BUTTON_PIN)
        

        self.button.when_pressed = self.button_interaction_wrapper


        self.btn_interaction_resolver: Future | None = None
        self.event_loop: asyncio.AbstractEventLoop = event_loop
        self.await_confirm = False


    def inject_cmd(self, cmd:"CmdTyping"):
        self.cmd = cmd
        self.reset_button.when_pressed = cmd.recorder.reset_recordings

    def _initialize_button(self, pin: int) -> Button:
        return Button(pin, pull_up=True, bounce_time=0.05)
    
    def button_await_confirm(self, state:bool) -> None:
        self.await_confirm = state

    async def _handle_button_press(self):

        # Duration to distinguish short/long press
        threshold = 0.15
        polling_interval = 0.01
        elapsed = 0

        # Breaks when holding threshold reached
        # Breaks when button is released
        while self.button.is_pressed and elapsed < threshold:
            await asyncio.sleep(polling_interval)
            elapsed += polling_interval

        # Button is released after the while loop
        if not self.button.is_pressed:
            self.cmd.player.skip()
        # Button is still held after the hold threshold reached
        else:
            self.cmd.recorder.start_recording()

            # Wait until release
            while self.button.is_pressed:
                await asyncio.sleep(polling_interval)
            
            self.cmd.recorder.stop_recording()


    async def _confirm_or_delete(self):
        self.button.when_pressed = None  # disable reentry
        confirm_led_threshold = 2.5
        hold_threshold = 2.8
        short_threshold = 0.23
        polling_interval = 0.01

        press_start = time.monotonic()
        proc = self.cmd.player.playback_hold_confirm()
        led_task = self.cmd.led.start_confirm_led_seq(hold_threshold)

        # Wait while button is held
        while self.button.is_pressed:
            await asyncio.sleep(polling_interval)
            if time.monotonic() - press_start > confirm_led_threshold:
                self.cmd.led.led_on((0, 20, 0))

        press_duration = time.monotonic() - press_start

        self.cmd.player.terminate_current_playback(proc)
        self.cmd.led.stop_led_task(led_task)
        self.cmd.player.resume()

        if press_duration >= hold_threshold:
            self.cmd.player.pause()
            # Confirm
            print("Confirmed via hold")

            self.cmd.player.extend_buffer()
            self.cmd.led.start_delayed_led_off(1)

            await asyncio.sleep(2)
            self.cmd.player.stop_confirmation_loop()
            self.cmd.player.resume()
            self.await_confirm = False

        elif press_duration <= short_threshold:
            self.cmd.player.pause()
            # Delete
            print("Deleted via short press")
            self.cmd.player.playback_delete()

            self.cmd.recorder.delete_recording()
            self.cmd.led.start_deleted_led_seq(1.5)

            await asyncio.sleep(2)
            self.cmd.player.stop_confirmation_loop()
            self.cmd.player.resume()
            self.await_confirm = False

        else:
            # In-between press, do nothing
            print(f"Ignored press duration: {press_duration:.2f}s")
        
        self.button.when_pressed = self.button_interaction_wrapper

    # double press too complex timing wise
    async def _confirm_press_advanced(self):
        self.button.when_pressed = None
        hold_threshold = 3.0  # seconds
        double_press_window = 0.5
        polling_interval = 0.01
        elapsed = 0.0

        proc = self.cmd.player.playback_hold_confirm()
        led_task = self.cmd.led.start_confirm_led_seq(hold_threshold)
        while self.button.is_pressed and elapsed < hold_threshold:
            await asyncio.sleep(polling_interval)
            elapsed += polling_interval
        


        if elapsed >= hold_threshold:
            # to terminate the confirmation loop, but should not affect original loop
            self.cmd.player.stop_confirmation_loop()

            # because player stopped in cmd.playback_hold_confirm() and player pause is affecting original play forever loop
            self.cmd.player.resume()
            self.cmd.player.terminate_current_playback(proc)
            
            # Reset button.when_pressed
            self.button.when_pressed = self.button_interaction_wrapper
            # confirmed recording. extend with current recording
            print("Confirmed Track")
            self.cmd.player.extend_buffer()
            # disable confirm_press path in interaction_wrapper
            self.await_confirm = False
            self.cmd.led.start_delayed_led_off(1)
            return
        

        self.cmd.led.stop_led_task(led_task)
        # Released early — check for second press (double-press)
        self.cmd.player.terminate_current_playback(proc)
        self.cmd.player.resume()


        if await self._wait_for_second_press(double_press_window):
            print("Double press — delete track")
            self.cmd.led.start_deleted_led_seq(1.5)
            self.cmd.player.pause()
            self.cmd.player.stop_confirmation_loop()
            self.cmd.recorder.delete_recording()
            self.cmd.player.resume()
            self.await_confirm = False
        else:
            print("Double press not acknowledged")

    async def _wait_for_second_press(self, timeout: float) -> bool:
        second_press_event = asyncio.Event()

        def on_second_press():
            second_press_event.set()

        self.button.when_pressed = on_second_press

        try:
            await asyncio.wait_for(second_press_event.wait(), timeout=timeout)
            press_start = time.time()
            while self.button.is_pressed:
                await asyncio.sleep(0.01)
            press_duration = time.time() - press_start
            return press_duration < 0.15
        except asyncio.TimeoutError:
            return False
        finally:
            self.button.when_pressed = self.button_interaction_wrapper

    def button_interaction_wrapper(self):
        
        self.cmd.led.led_off()
        if self.btn_interaction_resolver is None or self.btn_interaction_resolver.done():
        # handle await stuff in new coroutine
            if self.await_confirm:
                self.btn_interaction_resolver = asyncio.run_coroutine_threadsafe(self._confirm_or_delete(), self.event_loop)

            else:
                self.btn_interaction_resolver = asyncio.run_coroutine_threadsafe(self._handle_button_press(), self.event_loop)


            