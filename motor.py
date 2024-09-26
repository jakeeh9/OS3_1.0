import RPi.GPIO as gpio
import time
import csv

MAX_FREQ = 9600

PAN_ENABLE = 29
TILT_ENABLE = 23

# Read CSV file into list to create acceleration profile
ramp = []
with open('ramp.csv', 'r') as file:
    fileRow = csv.reader(file)
    for row in fileRow:
        ramp.append(float(row[0]))
rampMaxIndex = len(ramp) - 1
minDelay = min(ramp)

class motor:
    def __init__(self, pins):
        # Set internal variables for GPIO pins
        self.direction = pins[0]
        self.step = pins[1]
        self.M0 = pins[2]
        self.M1 = pins[3]
        self.enable = pins[4]
        self.switch1 = pins[5]
        self.switch2 = pins[6]
        self.position = 0
        self.uSteps = 0
        self.totalSteps = 0
        self.maxStep = 0
        self.minStep = 0
        #print("Created motor object with step pin: ", self.step)


    def motorInit(self):
        ####### motorInit #######
        # Function:
        # - Set the GPIO mode for the motor control pins
        # - Configure the motor driver microstepping resolution
        #
        # Inputs: None
        #
        # Return Values: None
        ##########################

        # Set GPIO pins to correct mode
        gpio.setup(self.direction, gpio.OUT)
        gpio.setup(self.step, gpio.OUT)
        gpio.setup(self.M0, gpio.OUT)
        gpio.setup(self.M1, gpio.OUT)
        gpio.setup(self.enable, gpio.OUT)
        gpio.setup(self.switch1, gpio.IN)
        gpio.setup(self.switch2, gpio.IN)

        #Disable motor
        gpio.output(self.enable, gpio.HIGH)

        # Set the resolution of the motor driver
        # M1 = 1, M0 = 1 - 16uStep/step
        # to get M0 = Z, set M0 to input with no PU/PD resistors
        gpio.output(self.M0, gpio.HIGH)
        gpio.output(self.M1, gpio.HIGH)
        self.uSteps = 16    # Update this value if changing the resolution




    def run(self, clockwise, angle, targetSpeed, lock, reverse = False):
        ######## run ########
        # Function: Run the motor for specified parameters
        #
        # Inputs:
        # - clockwise: the directio to turn the motor. 0 = Anticlockwise, 1 = Clockwise
        # - angle: The angle through which the motor should turn (in degrees)
        # - targetSpeed: The desired target speed in RPM. Will be limited if given value is too high.
        # - lock: threading lock needed for multithreading
        # - reverse: allows the motor to reverse without immediately triggering the switch again
        #
        # Return Values:
        # No return values. Position is tracked as part of the motor object
        ##########################

        lock.acquire()
        lock.release()

        """
        # For testing purposes
        if self.step == 38:
            motorName = "Pan"
        else:
            motorName = "Tilt"
        print("=== Running motor ===")
        print("Motor: ", motorName)
        print("Direction:", clockwise)
        print("Target Speed: ", targetSpeed)
        print("Angle: ", angle)
        """

        # Find the number of pulses needed
        degPerStep = 1.8/self.uSteps
        steps = int(angle/degPerStep)
        #print("Steps:", steps)

        # Calculate the frequency of pulses needed to rotate at the target speed
        targetFreq = ((360/degPerStep)*targetSpeed)/60
        if targetFreq > MAX_FREQ:                          # Limit to pre-set max frequency
            targetFreq = MAX_FREQ
        targetMinDelay = 1/(2*targetFreq)

        # Set the direction for the motor to move
        if clockwise:
            gpio.output(self.direction, gpio.HIGH)
        else:
            gpio.output(self.direction, gpio.LOW)

        delay = []

        # Find index in accel profile of the target speed's delay
        for i in ramp:
            if i <= targetMinDelay:
                stopIndex = ramp.index(i)
                #print("Stop Index: ", stopIndex)
                break

        # Find the step number to stop accelerating or start decelerating
        if steps > 2* stopIndex:
            stopAccel = stopIndex
            startDecel = (steps - 1) - stopIndex
        else:
            stopIndex = round(steps/2) - 1
            stopAccel = stopIndex
            startDecel = stopIndex + 1

        # Fill in array containing all the relevant delays
        # Should work for runs where targetMinDelay is not reached
        for i in range(steps):
            if i <= stopAccel:
                delay.append(ramp[i])
            elif i > stopAccel and i < startDecel:
                delay.append(targetMinDelay)
            else:
                delay.append(ramp[rampMaxIndex-((steps-1)-i)])
                
        # Send one pulse per required step
        gpio.output(self.enable, gpio.LOW)
        for i in range(steps):
            # Increment/decrement tracked position
            if clockwise:
                self.position = self.position + 1
            else:
                self.position = self.position - 1
            gpio.output(self.step, gpio.HIGH)
            time.sleep(delay[i])
            gpio.output(self.step, gpio.LOW)
            time.sleep(delay[i])
            if (gpio.input(self.switch1) == gpio.LOW or gpio.input(self.switch2) == gpio.LOW) and not reverse:
                print("Switch Pressed!")
                time.sleep(0.5)
                self.run(not clockwise, 90, 60, lock, True)
                break
        gpio.output(self.enable, gpio.HIGH)  


    def fullCalibrate(self, threadLock):
        ####### Full Calibration #######
        # Function: Calibrate incl. finding total no. of steps
        #
        # Inputs:
        # - threadLock: thread lock object for multithreading. Unused now as motor run has been moved out of this function
        #
        # Return Values: None
        ################################

        freq = 2000
        stop = False
        gpio.output(self.direction, gpio.LOW)
        gpio.output(self.enable, gpio.LOW)

        # Run in one direction
        print("Direction 1")
        while(not stop):
            gpio.output(self.step, gpio.HIGH)
            time.sleep(1/(2*freq))
            gpio.output(self.step, gpio.LOW)
            time.sleep(1/(2*freq))
            if gpio.input(self.switch1) == gpio.LOW or gpio.input(self.switch2) == gpio.LOW:
                print("Switch Pressed!")
                stop=True
        time.sleep(0.5)
        self.totalSteps = 0
        gpio.output(self.direction, gpio.HIGH)
        stop = False

        # Run in the other direction
        print("Direction 2")
        while(not stop):
            gpio.output(self.step, gpio.HIGH)
            self.totalSteps = self.totalSteps + 1
            time.sleep(1/(2*freq))
            gpio.output(self.step, gpio.LOW)
            time.sleep(1/(2*freq))
            if (gpio.input(self.switch1) == gpio.LOW or gpio.input(self.switch2) == gpio.LOW) and self.totalSteps > 100:
                stop = True
        gpio.output(self.enable, gpio.HIGH)
        time.sleep(0.2)
        self.position = self.totalSteps/2
        self.maxStep = self.position
        self.minStep = -self.position
                    


    def calibrate(self, threadLock):
    ####### calibrate #######
    # Function: Run the motor in one direction until the limit switch has been hit. Reset tracked position
    #
    # Inputs:
    # - threadLock: thread lock object for multithreading. Unused now as motor run has been moved out of this function
    #
    # Return Values: None
    ##########################

        freq = 2000
        stop = False
        gpio.output(self.direction, gpio.HIGH)
        gpio.output(self.enable, gpio.LOW)
        while(not stop):
            gpio.output(self.step, gpio.HIGH)
            time.sleep(1/(2*freq))
            gpio.output(self.step, gpio.LOW)
            time.sleep(1/(2*freq))
            if gpio.input(self.switch1) == gpio.LOW or gpio.input(self.switch2) == gpio.LOW:
                stop = True
        gpio.output(self.enable, gpio.HIGH)
        time.sleep(0.2)
        self.position = self.totalSteps/2
        self.maxStep = self.position
        self.minStep = -self.position