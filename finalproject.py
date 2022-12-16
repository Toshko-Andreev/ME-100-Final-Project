from mqttclient import MQTTClient
import network
import sys
from machine import Pin, I2C
from board import SDA, SCL
import time
from board import LED
from ina219 import INA219
from datetime import datetime

#------------------------------------------------------------------------------------------------------------------------------
#Initializations
#------------------------------------------------------------------------------------------------------------------------------
#The initialization of the state
state = {"button":False, "home":True, "bright":False, "tod":True}

#Initialization of motor pins
motor_red = Pin(27, mode=Pin.OUT)
motor_black = Pin(33, mode=Pin.OUT)

#Initialize LED
led = Pin(LED, mode=Pin.OUT)

#Initialize the ina219
i2c = I2C(id=0, scl=Pin(SCL), sda=Pin(SDA), freq=100000)
SHUNT_RESISTOR_OHMS = 0.1
ina = INA219(SHUNT_RESISTOR_OHMS, i2c)
ina.configure()

#------------------------------------------------------------------------------------------------------------------------------
#MQTT Communication with Adafruit Feed
#------------------------------------------------------------------------------------------------------------------------------
# Check wifi connection
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
ip = wlan.ifconfig()[0]
if ip == '0.0.0.0':
    print("no wifi connection")
    sys.exit()
else:
    print("connected to WiFi at IP", ip)

# Set up Adafruit connection
adafruitIoUrl = 'io.adafruit.com'
adafruitUsername = 'Toshko'
adafruitAioKey = 'aio_lHOX93ERpMPHLjlPQvAYDpYxwJ56'

# Define callback function
def sub_cb(topic, msg):
    print("The message is: " + str((topic, msg)))
    if msg.decode() == "button press":
        if state["home"]:
            flick_up()
        state["button"] = True
    elif msg.decode() == "left home":
        print("left home")
        if state["bright"]:
            flick_down()
        state["home"] = False
    elif msg.decode() == "got home":
        state["home"] = True
        if not state["bright"]:
            flick_up()
    elif msg.decode() == "button depress":
        if state["home"]:
            flick_down()
        state["button"] = False


# Connect to Adafruit server
print("Connecting to Adafruit")
mqtt = MQTTClient(adafruitIoUrl, port='1883', user=adafruitUsername, password=adafruitAioKey)
time.sleep(0.5)
print("Connected!")

# This will set the function sub_cb to be called when mqtt.check_msg() checks
# that there is a message pending
mqtt.set_callback(sub_cb)

feedName = "Toshko/feeds/light-switch"
feedMessage = 'We are good to go!'
mqtt.publish(feedName, feedMessage)
mqtt.subscribe(feedName)

#------------------------------------------------------------------------------------------------------------------------------
#Motor Functions
#------------------------------------------------------------------------------------------------------------------------------
#Reverses the motor
def flick_down():
    print("Flicked down")
    led(1)
    motor_red(1)
    motor_black(0)
    time.sleep(2)
    led(0)
    motor_red(0)
    motor_black(0)

#Drives the motor forward
def flick_up():
    print("Flicked up")
    led(1)
    motor_red(0)
    motor_black(1)
    time.sleep(2)
    led(0)
    motor_red(0)
    motor_black(0)

#------------------------------------------------------------------------------------------------------------------------------
#The main while loop
#------------------------------------------------------------------------------------------------------------------------------
darkness = 0
turnoff = False

#The main while loop
while True:
    #if it's been dark for over a minute, reset the darkness timer and turn on the lights
    if darkness >= 60:
        mqtt.publish(feedName, "It's dark. Turning on the lights!")
        darkness = 0
        state["bright"] = False
        if state["home"] and state["tod"]:
            flick_up()

    #increment darkness timer
    if ina.voltage() < 1.2:
        darkness = darkness + 1
    elif ina.voltage > 1.2:
        state["bright"] = True
        darkness = 0

    #check to see if it's sleep time
    now = datetime.now()
    hour = int(now.strftime("%H"))
    if hour <= 9:
        state["tod"] = False
        #if it hasn't been turned off, turn off at midnight and say it's been turned off
        if not turnoff:             
            flick_down()
            turnoff = True
    else:
        turnoff = False
        state["tod"] = True

    #check mqtt and sleep for a second
    mqtt.check_msg()
    time.sleep(1)