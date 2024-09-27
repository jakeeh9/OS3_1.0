# Optical Space Surveillance Station (OS3)

This is the first post-dissertation-submission version of the OS3 Raspberry Pi Control software. The software must run on a Raspberry Pi configured with all the appropriate python modules.

## Installation Instructions
### Python Modules
The software depends on a number of python modules and other software that must also be installed to the Raspberry Pi.
Most of the required modules are pre-installed with the Raspberry Pi OS. You must manually install the GPhoto2 python interface:
`python3 -m pip install gphoto2`

### Other Setup
#### GPhoto2
The GPhoto2 software is used to control the camera. The installation process is a bit convoluted, but [this guide](https://pimylifeup.com/raspberry-pi-dslr-camera-control/) provides step-by-step instructions to set it up and test it.

#### GPS Time
_Don't worry about it for now, the Raspberry Pi I used is already set up and I can't remeber how I did it. I will update this at some point when I work out how to do it again..._

#### Auto-Run
To make this much easier to use, the python files can be configured to auto-run when the Pi starts up.

##### Configure the Pi to run `boot.py` on startup to configure GPIO:
- Edit the rc.local file: `sudo nano /etc/rc.local`
- Add the following lines before the `exit 0` line:
    ```
    cd /
    python3 /home/pi/Documents/OS3_1.0/boot.py
    ```

##### Run the OS3 software at log in:
- Edit the .bashrc file: `sudo nano /home/pi/.bashrc`
- Add the following lines at the end of the file:
    ```
    cd /home/pi/Documents/OS3_1.0
    python3 OS3_1.0.py
    ```

##### Auto-Mount USB Drives
- Create the directory for the USB drive (already done on the Pi I used): `sudo mkdir /mnt/usb`
- Find the UUID of your USB drive: `sudo ls -l /dev/disk/by-uuid/`
    - on the line ending sda1, find the UUID in the format FFFF-FFFF and make a note of it
- Edit the fstab file: `sudo nano /etc/fstab`
- Add the following line to the end:
    ```
    UUID=FFFF-FFFF /mnt/usb vfat uid=pi,gid=pi 0 0
    ```
- Reboot the Pi

##### Enable Auto log-in
- Use the Raspi-config tool to enable auto log in by running `sudo raspi-config`
- Go to System > log in > console with auto login. _This might not be exactly how the menu is worded in the OS_

## Run Instructions
With auto-run enabled, the software should run automatically when the Raspberry Pi is turned on. It may take around 30-60 seconds to boot up and start running.

If you're regularly accessing the Pi with SSH, disable auto login. The software will then run as soon as you make the SSH connection.

The software can be stopped at any time by using `ctrl + c`. If the motor is moving, the movement will finish before the software exits.

## Future Changes
- I have plans to work on an installer that will automatically download all the relevant software and python modules and do as much of the configuration as possible.

## Credits
Authors: Jake Heath  
Email: jh02041@surrey.ac.uk

Developed in collaboration with: James Morbin, University of Surrey