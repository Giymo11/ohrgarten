

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

use setup.sh to install dependencies: `chmod +x setup.sh && ./setup.sh`

# notes



