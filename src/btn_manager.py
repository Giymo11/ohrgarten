from config import ButtonConfig
from gpiozero import Button
from cmd_typing import CmdTyping
import asyncio
from asyncio import Event
from concurrent.futures import Future
from typing import TYPE_CHECKING

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
        self.reset_button.when_pressed = cmd.reset_recordings

    def _initialize_button(self, pin: int) -> Button:
        return Button(pin, pull_up=True, bounce_time=0.1)
    
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
            self.cmd.skip_player()
        # Button is still held after the hold threshold reached
        else:
            self.cmd.start_recording()

            # Wait until release
            while self.button.is_pressed:
                await asyncio.sleep(polling_interval)
            
            self.cmd.stop_recording()


    async def _confirm_press(self):
        self.button.when_pressed = None
        hold_threshold = 3.0  # seconds
        polling_interval = 0.01
        elapsed = 0.0

        self.cmd.playback_hold_confirm()
        while self.button.is_pressed and elapsed < hold_threshold:
            await asyncio.sleep(polling_interval)
            elapsed += polling_interval


        if elapsed >= hold_threshold:
            self.cmd.stop_player()
            self.cmd.resume_player()
            print("Confirmed Track")
            self.button.when_pressed = self.button_interaction_wrapper
            # confirmed recording. extend with current recording
            self.cmd.extend_buffer()
            self.await_confirm = False
            return
        else:
            self.cmd.resume_player()
            elapsed = 0.0
            while not self.button.is_pressed and elapsed < 0.5:
                await asyncio.sleep(polling_interval)
                elapsed += polling_interval
            
            if self.button.is_pressed:
                elapsed = 0.0
                while self.button.is_pressed and elapsed < 0.15:
                    await asyncio.sleep(polling_interval)
                    elapsed += polling_interval
                
                if not self.button.is_pressed:
                    print("Delete Track")
            self.button.when_pressed = self.button_interaction_wrapper  


    def button_interaction_wrapper(self):

        if self.btn_interaction_resolver is None or self.btn_interaction_resolver.done():
        # handle await stuff in new coroutine
            if self.await_confirm:
                self.btn_interaction_resolver = asyncio.run_coroutine_threadsafe(self._confirm_press(), self.event_loop)


            else:
                self.btn_interaction_resolver = asyncio.run_coroutine_threadsafe(self._handle_button_press(), self.event_loop)


            