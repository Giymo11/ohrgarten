

## to setup raspberry

1. use your favorite imager, i used `USBImager`
2. connect using hdmi, mouse, keyboard (is easiest i found)
3. use `sudo raspi-config` to enable ssh (interface options) and wifi (system options)
4. use `remote - ssh` extension in vscode to develop on the raspi using ssh

## setup python env

1. create a virtual environment using `python3 -m venv venv`
2. activate it using `source venv/bin/activate`
4. when you are done, you leave the venv with `deactivate`

use `pip freeze > requirements.txt` to record the dependencies

## install deps
Make sure the raspberry pi is correctly configured to use use piwheels.
`pip config set global.index-url https://www.piwheels.org/simple`
use setup.sh to install dependencies: `chmod +x setup.sh && ./setup.sh`

## start the script
1) activate venv
2) run `sh start.sh`

This will run the script with root privileges, which is required for the Neopixel library.

## notes

the volume is bound to individual sound cards. With `aplay -l` find the index of the soundcard whose volume needs to be adjusted.
Use `alsamixer -c <soundcard index>` to change the speaker volume interactively.
Use `amixer -c <soundcard index> sset Speaker 100%` to change the Speaker volume directly.

example:
`amixer -c 2 sset Speaker 50%` sets the soundcard at index 2s speaker to 50%

These settings do not persist on reboot. Use `sudo alsactl store` to store the current state instead and `sudo alsactl restore` to restore the state.
If alsa-restore.service is configured (by default), the state will be restored on reboot as well.

