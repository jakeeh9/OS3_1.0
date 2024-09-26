import RPi.GPIO as gpio

gpio.setwarnings(False)
gpio.setmode(gpio.BOARD)
gpio.setup(19, gpio.OUT)
gpio.setup(23, gpio.OUT)
gpio.setup(38, gpio.OUT)
gpio.output(19, gpio.HIGH)
gpio.output(23, gpio.HIGH)
gpio.output(38, gpio.HIGH)