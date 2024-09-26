# OS3 Version 1.0

# Import relevant files
import RPi.GPIO as gpio
import gphoto2 as gp
import threading
import time
import csv
import numpy
import math
import shutil
from datetime import datetime
from motor import motor
from scheduleManager import Schedule

# Define & setup motor control pins and limit switch input
# CONFIG pins put motor driver into INDEX mode
# M0 and M1 pins are used to set the step size

# Maximum pulse frequency from motor driver datasheet
MAX_FREQ = 9600

# Ratio of mount to pulley movement
PAN_BELT_RATIO = 35.27
TILT_BELT_RATIO = 17.5

TILT_0_ANGLE = 468.79

# For PAN motor controller
PAN_DIRECTION = 33  # Connecs to DIR pin
PAN_STEP = 31       # Connect to STEP pin
PAN_M0 = 37         # Connect to M0 Pin
PAN_M1 = 35         # Connect to M1 Pin
PAN_ENABLE = 29     # Connect to nENBL Pin
PAN_SW_1 = 3        # End stop limit swicth 1
PAN_SW_2 = 5        # End stop limit switch 2
PAN_PINS = [PAN_DIRECTION, PAN_STEP, PAN_M0, PAN_M1, PAN_ENABLE, PAN_SW_1, PAN_SW_2]


# For TILT motor controller
TILT_DIRECTION = 19 # Connecs to DIR pin
TILT_STEP = 21      # Connect to STEP pin
TILT_M0 = 13        # Connect to M0 Pin
TILT_M1 = 15        # Connect to M1 Pin
TILT_ENABLE = 23    # Connect to nENBL Pin
TILT_SW_1 = 7       # End stop limit swicth 1
TILT_SW_2 = 11      # End stop limit switch 2
TILT_PINS = [TILT_DIRECTION, TILT_STEP, TILT_M0, TILT_M1, TILT_ENABLE, TILT_SW_1, TILT_SW_2]


YELLOW_LED = 40     # Yellow software controlled LED
RED_LED = 38        # Red software controlled LED
LED_FREQ = 15

skipCalibration = False  # Skip the auto-calibration on startup (for testing without motors connected)
copySchedule = True     # Copy the schedule from USB drive. If False, the schedule will be taken from current directory
copyLog = True          # Copy the log file to the USB drive. The file will also be in the current directory

FILE_SOURCE = "/mnt/usb/schedule.csv"


def setCamera(setShutterSpeed = "N", setAperture = "N"):
    ######## setCamera ########
    # Function: Set camera shutter speed and aperture
    #
    # Inputs:
    # - setShutterSpeed: optional. Enter desired shutter speed as str
    # - setAperture: optional. Enter desired aperture as str
    #
    # Return Values: None
    ##########################
    if cameraConnected:
        if setShutterSpeed != "N" or setAperture != "N":
            try:
                config = camera.get_config()
            except:
                print("Error: Camera Disconnected.")
                return
            if setShutterSpeed != "N":
                OK, shutterSpeedConfig = gp.gp_widget_get_child_by_name(config, 'shutterspeed')
                if OK >= gp.GP_OK:
                    print("Setting shutter speed to ", setShutterSpeed)
                    shutterSpeedConfig.set_value(setShutterSpeed)
            if setAperture != "N":
                OK, apertureConfig = gp.gp_widget_get_child_by_name(config, 'aperture')
                if OK >= gp.GP_OK:
                    print("Setting aperutre to ", setAperture)
                    apertureConfig.set_value(setAperture)
            try:
                camera.set_config(config)
            except:
                print("Error: Camera Disconnected.")
                return
            time.sleep(0.1)
        else:
            print("No arguments given.")
    else:
        print("Cannot set values without camera connected.")


def takeImage(satelliteName, numInSequence, logFile):
    ######## takeImage ########
    # Function: Start camera exposure
    #
    # Inputs:
    # - satelliteName: target name to print in the log file
    # - numInSequene: sequence number to print in log file
    # - logFile: fileobject for the log file
    #
    # Return Values: None
    ##########################
    ledOn = gpio.input(YELLOW_LED)
    gpio.output(YELLOW_LED, gpio.LOW)
    if cameraConnected:
        imageTime = datetime.utcnow()
        try:
            filePath = camera.capture(gp.GP_CAPTURE_IMAGE)
        except:
            print("Error: Camera Disconnected.")
        logFile.write("\n" + filePath.name + "," + satelliteName + "," + imageTime.strftime("%H:%M:%S") + "," + str(numInSequence))
    else:
        gpio.output(RED_LED, gpio.HIGH)
        print("Cannot take image without camera connected.")
        time.sleep(0.5)
        gpio.output(RED_LED, gpio.LOW)
    if ledOn:
        gpio.output(YELLOW_LED, gpio.HIGH)
    return



def calcRotation(azimuth, elevation):
    ######## calcRotation ########
    # Function: Find the angle to rotate each motor
    #
    # Inputs:
    # - azimuth: The target azimuth angle in degrees
    # - elevation: The target elevation angle in degrees
    #
    # Return Values:
    # - success: Boolean. False if target position can't be reached
    # - panRotation: required rotation of the pan motor
    # - tiltRotation: required rotation of the tilt motor
    ##########################
    ROTATION_ANGLE = math.radians(-40)
    azimuth = math.radians(azimuth)
    elevation = math.radians(elevation)
    
    posE = math.sin(azimuth) * math.cos(elevation)
    posN = math.cos(azimuth) * math.cos(elevation)
    posU = math.sin(elevation)

    RposE = posE
    RposN = (posN * math.cos(ROTATION_ANGLE)) + (posU * math.sin(ROTATION_ANGLE))
    RposU = (-posN * math.sin(ROTATION_ANGLE)) + (posU * math.cos(ROTATION_ANGLE))

    mountAzimuth = math.atan2(RposE, RposN)
    mountElevation = math.asin(RposU)

    mountAzimuth = math.degrees(mountAzimuth)
    mountElevation = math.degrees(mountElevation)

    currentPanAngle = (pan.position*(1.8/pan.uSteps)) / PAN_BELT_RATIO
    currentTiltAngle = (tilt.position*(1.8/tilt.uSteps)) / TILT_BELT_RATIO


    success = True
    if mountAzimuth > (pan.maxStep*(1.8/pan.uSteps)) / PAN_BELT_RATIO:
        mountAzimuth = mountAzimuth - 180
        mountElevation = 180 - mountElevation
    elif mountAzimuth < (pan.minStep*(1.8/pan.uSteps)) / PAN_BELT_RATIO:
        mountAzimuth = mountAzimuth + 180
        mountElevation = 180 - mountElevation

    mountElevation = -mountElevation

    if mountAzimuth < (pan.maxStep*(1.8/pan.uSteps)) / PAN_BELT_RATIO and mountAzimuth > (pan.minStep*(1.8/pan.uSteps)) / PAN_BELT_RATIO:
        panRotation = PAN_BELT_RATIO*(mountAzimuth - currentPanAngle)
    else:
        panRotation = 0
        success = False

    if mountElevation < (tilt.maxStep*(1.8/tilt.uSteps)) / TILT_BELT_RATIO and mountElevation > (tilt.minStep*(1.8/tilt.uSteps)) / TILT_BELT_RATIO:
        tiltRotation = TILT_BELT_RATIO*(mountElevation - currentTiltAngle)
    else:
        tiltRotation = 0
        success = False
    
    return success, panRotation, tiltRotation



####### MAIN #######
gpio.setwarnings(False)
gpio.setmode(gpio.BOARD)
cameraConnected = False

# Define motor objects and assign their pins
pan = motor(PAN_PINS)
tilt = motor(TILT_PINS)

# Define schedule object
schedule = Schedule()

# Configure GPIO for each motor
pan.motorInit()
tilt.motorInit()


# Set up LED pins
gpio.setup(YELLOW_LED, gpio.OUT)
gpio.setup(RED_LED, gpio.OUT)
gpio.output(YELLOW_LED, gpio.LOW)
gpio.output(RED_LED, gpio.LOW)

# Used for multithreading of motors
threadLock = threading.Lock()

ledPulse = gpio.PWM(YELLOW_LED, LED_FREQ)

# Set up camera object and print summary of camera info
# Will ask to try again if no camera detected
# Allows you to continue without camera (won't take any images)
camera = gp.Camera()
cameraReady = False
while not cameraReady:
    try:
        camera.init()
        cameraSummary = camera.get_summary()
        print("Camera Summary")
        print("==============")
        print(str(cameraSummary))
        cameraConnected = True
        cameraReady = True
    except:
        validInput = False
        while not validInput:
            tryAgain = input("Error: Camera not detected. Try again? [y/n] ")
            if tryAgain == "N" or tryAgain == "n":
                while not validInput:
                    proceed = input("Proceed without camera? [y/n] ")
                    if proceed == "N" or proceed == "n":
                        print("Exiting...")
                        exit()
                    elif proceed == "Y" or proceed == "y":
                        print("Proceeding without camera.")
                        validInput = True
                        cameraReady = True
            elif tryAgain == "Y" or tryAgain == "y":
                validInput = True

if skipCalibration:
    # skip calibration should only be used for testing
    print("Calibration Skipped.")
    pan.totalSteps = 60210
    pan.maxStep = 60210/2
    pan.minStep = -60210/2
    tilt.totalSteps = 47491
    tilt.maxStep = 4167
    tilt.minStep = -43324
    print("Pan total steps:", pan.totalSteps)
    print("Tilt total steps:", tilt.totalSteps)
else:
    # Look for calibraion file
    calibrationFileExists = False
    try:
        calibrationFile = open("calibration.csv", "x")
    except FileExistsError:
        calibrationFileExists = True

    ledPulse.ChangeFrequency(LED_FREQ)
    ledPulse.start(50)
    if calibrationFileExists:
        # Load pre-existing calibration
        with open('calibration.csv', 'r') as calibrationFile:
                fileRow = csv.reader(calibrationFile)
                for row in fileRow:
                    if row[0] == "pan":
                        pan.totalSteps = int(row[1])
                    elif row[0] == "tilt":
                        tilt.totalSteps = int(row[1])
        print("Loaded calibration file.")
        print("Pan total steps:", pan.totalSteps)
        print("Tilt total steps:", tilt.totalSteps)
        time.sleep(1)
        print("Calibrating pan motor.")
        pan.calibrate(threadLock)
        pan.run(0, (pan.totalSteps/2) * (1.8/pan.uSteps), 60, threadLock, True)
        print("Calibrating tilt motor.")
        tilt.calibrate(threadLock)
        tilt.position = TILT_0_ANGLE / (1.8/tilt.uSteps)
        tilt.maxStep = tilt.position
        tilt.minStep = tilt.position - tilt.totalSteps
        tilt.run(0, TILT_0_ANGLE, 60, threadLock, True)
    else:
        # No calibration file - run full calibration
        print("Full calibration of pan motor.")
        pan.fullCalibrate(threadLock)
        pan.run(0, (pan.totalSteps/2) * (1.8/pan.uSteps), 60, threadLock, True)
        print("Full calibration of tilt motor.")
        tilt.fullCalibrate(threadLock)
        tilt.position = TILT_0_ANGLE / (1.8/tilt.uSteps)
        tilt.maxStep = tilt.position
        tilt.maxStep = tilt.position - tilt.totalSteps
        tilt.run(0, TILT_0_ANGLE, 60, threadLock, True)
        calibrationFile.write("pan," + str(pan.totalSteps) + "\ntilt," + str(tilt.totalSteps))
    calibrationFile.close()
    ledPulse.stop()



print("\nPan Position:", pan.position)
print("Tilt Position:", tilt.position)
print("\n")


# Read schedule file
if copySchedule:
    print("\nCopying Schedule...")
    if schedule.copyFile(FILE_SOURCE):
        print("Reading coppied schedule...")
        scheduleLoaded = schedule.open(schedule.filePath)
    else:
        print("Looking for schedule in current directory.")
        scheduleLoaded = schedule.open("schedule.csv")
else:
    print("\nReading Schedule from current directory...")
    scheduleLoaded = schedule.open("schedule.csv")


# Set camera parameters
setCamera(setShutterSpeed = "8", setAperture = "4.5")
shutterSpeed = 8 


if scheduleLoaded:
    # Set up log file, or open if it already exists
    # FUTURE CHANGE: PUT LOG FILES IN A SUB FOLDER
    print("Opening log file...")
    logFileName = datetime.utcnow().strftime("%Y%m%d") + ".csv"
    try:
        captureLog = open(logFileName, "x")
        captureLog.write("File Name, Target, Time, Number in Sequence")
    except FileExistsError:
        captureLog = open(logFileName, "a")


    # Loop through all satellites in the schedule
    for satellite in schedule.list[1:]:
        # Print info about the next target
        print("\n========== Next Satellite ==========")
        print(print("Name:", satellite[0]))
        print("Culmination Time:", satellite[4][11:19])
        print("Azimuth:", satellite[2])
        print("Elevation:", satellite[3])
        rotationValid, panRotation, tiltRotation = calcRotation(float(satellite[2]), float(satellite[3]))
        print("\nPan Rotation: ", panRotation)
        print("Tilt Rotation: ", tiltRotation)
        if not rotationValid:
            print("Error: Unable to reach target.")
            gpio.output(RED_LED, gpio.HIGH)
        print("====================================")
        print("Waiting...")

        # Convert time string to timestamp
        satelliteTime = datetime.strptime(str(satellite[4]), "%Y-%m-%d %H:%M:%S").timestamp()

        prevTime = datetime.utcnow()
        # Waiting for movement time
        while(datetime.utcnow().timestamp() < (satelliteTime - 120)):
            if datetime.utcnow() != prevTime:
                print("Current Time:", datetime.utcnow().strftime("%H:%M:%S"), "\r", end="")
                prevTime = datetime.utcnow()
        
        if rotationValid:
            print("Moving to position for", satellite[0])
            ledPulse.ChangeFrequency(LED_FREQ)
            ledPulse.start(50)
            if panRotation < 0:
                m1 = threading.Thread(target=pan.run, args=(0, abs(panRotation), 60, threadLock))
            else:
                m1 = threading.Thread(target=pan.run, args=(1, panRotation, 60, threadLock))
            m1.start()

            time.sleep(0.2)
            if tiltRotation < 0:
                m2 = threading.Thread(target=tilt.run, args=(0, abs(tiltRotation), 60, threadLock))
            else:
                m2 = threading.Thread(target=tilt.run, args=(1, tiltRotation, 60, threadLock))
            m2.start()

            m1.join()
            m2.join()
            ledPulse.stop()
            print("Pan Position:", pan.position)
            print("Tilt position:", tilt.position)
            time.sleep(0.2)

            # Imaging Sequence
            # Wait until 20s before culmination
            print("Waiting to take images...")
            gpio.output(YELLOW_LED, gpio.HIGH)    
            while(datetime.utcnow().timestamp() < (satelliteTime - 20)):
                continue
            print("-20 seconds")
            takeImage(satellite[0], -2, captureLog)

            while(datetime.utcnow().timestamp() < (satelliteTime - 10)):
                continue
            print("-10 seconds")
            takeImage(satellite[0], -1, captureLog)

            while(datetime.utcnow().timestamp() < satelliteTime):
                continue
            print("Culmination")
            takeImage(satellite[0], 0, captureLog)

            while(datetime.utcnow().timestamp() < (satelliteTime + 10)):
                continue
            print("+10 seconds")
            takeImage(satellite[0], 1, captureLog)

            while(datetime.utcnow().timestamp() < (satelliteTime + 20)):
                continue
            print("+20 seconds")
            takeImage(satellite[0], 2, captureLog)

            gpio.output(YELLOW_LED, gpio.LOW)

        else:
            print("Position unreachable.")
            print("Skipping", satellite[0], "\n")
            time.sleep(0.5)
            gpio.output(RED_LED, gpio.LOW)

    captureLog.close()

    # After test, return to default position
    print("Returning to home position.")
    rotationValid, panRotation, tiltRotation = calcRotation(0, -40)
    ledPulse.ChangeFrequency(LED_FREQ)
    ledPulse.start(50)
    if panRotation < 0:
        m1 = threading.Thread(target=pan.run, args=(0, abs(panRotation), 60, threadLock))
    else:
        m1 = threading.Thread(target=pan.run, args=(1, panRotation, 60, threadLock))
    m1.start()

    time.sleep(0.2)
    if tiltRotation < 0:
        m2 = threading.Thread(target=tilt.run, args=(0, abs(tiltRotation), 60, threadLock))
    else:
        m2 = threading.Thread(target=tilt.run, args=(1, tiltRotation, 60, threadLock))
    m2.start()

    m1.join()
    m2.join()
    ledPulse.stop()

    if copyLog:
        try:
            logFilePath = shutil.copy(logFileName, "/mnt/usb")
            print("Log file saved to", logFilePath)
        except:
            print("Could not copy log file. ")
else:
    print("No schedule open.")
    gpio.output(RED_LED, gpio.HIGH)