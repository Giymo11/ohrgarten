from gpiozero import Button
import time

# Replace with your actual GPIO pin number
BUTTON_PIN = 17  # GPIO17 = physical pin 11

# Initialize the button with pull-up (most common setup)
button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.1)

print("Waiting for button press (Press Ctrl+C to exit)...")

try:
    while True:
        if button.is_pressed:
            print("Button is pressed")
        else:
            print("Button is not pressed")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nExiting.")