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
        #button.when_released = stop_recording


        self.btn_interaction_resolver: Future | None = None
        self.btn_release_event = Event()
        self.event_loop: asyncio.AbstractEventLoop = event_loop


    def inject_cmd(self, cmd:"CmdTyping"):
        self.cmd = cmd
        self.reset_button.when_pressed = cmd.reset_recordings

    def _initialize_button(self, pin: int) -> Button:
        return Button(pin, pull_up=True, bounce_time=0.1)
    
        
        
    def _default_button_release_callback(self):
        self.event_loop.call_soon_threadsafe(self.btn_release_event.set)

    async def _handle_button_press(self):

        # Reset the event each time the button is pressed
        self.btn_release_event.clear()
        self.button.when_released = self._default_button_release_callback

        # Wait for either 1 second = threshold for long hold (recording)
        # Or event to be set when the button is released before that threshold
        done, pending = await asyncio.wait(
            [
                asyncio.create_task(asyncio.sleep(1)),
                asyncio.create_task(self.btn_release_event.wait())
            ],
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        if self.btn_release_event.is_set():
            # Button was released before 1 second = short press

            if getattr(self.button, "when_released", None) is not None:
                # use this to supress warnings regarding ``if self.button.when_released:``
                # Check to avoid warning on assigning None to previously None callback
                self.button.when_released = None
            self.cmd.skip_player()
        else:
            # Button is still held after 1 second = long press
            self.button.when_released = self.cmd.stop_recording 
            self.cmd.start_recording()


    def button_interaction_wrapper(self):

        if getattr(self.button, "when_released", None) is not None:
            self.button.when_released = None

        # handle await stuff in new coroutine
        if self.btn_interaction_resolver is None or self.btn_interaction_resolver.done():
            self.btn_interaction_resolver = asyncio.run_coroutine_threadsafe(self._handle_button_press(), self.event_loop)

    