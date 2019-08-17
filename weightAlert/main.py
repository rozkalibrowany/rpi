#! /usr/bin/python2
#  main program for weight measuring (hx711) and handling email communication (smtp and imap)
#  author: Karol Siegieda

import time
import sys
from email_handler import Class_eMail

import RPi.GPIO as GPIO
from hx711 import HX711

EMAIL_ID = ""
N_SAMPLES = 10
TIME_INTERVAL = 0.5
REFERENCE = -435
TIME_LIMIT_L2 = 16
TIME_LIMIT_L1 = 6
MIN_WEIGHT = 100
# sensor 1
DT1 = 25
SCK1 = 18
avgWeight = []

#***********************************************************#
class WeightSensor:
    def __init__(self, dt, sck):
        self.hx = None
        self.dt = dt
        self.sck = sck
        
#***********************************************************#

    def initializeGpio(self):
        self.hx = HX711(self.dt, self.sck)
        self.hx.set_reading_format("MSB", "MSB")
        self.hx.set_reference_unit(REFERENCE)
        #x.set_reference_unit(1)

        self.hx.reset()
        self.hx.tare()
        print ("Tare done! Add weight now...")

        # to use both channels, you'll need to tare them both
        #hx.tare_A()
        #hx.tare_B()
        
#***********************************************************#
     
    def getWeight(self):
        try:
            val = self.hx.get_weight(5)
            self.hx.power_down()
            self.hx.power_up()
            return (val)
        except (KeyboardInterrupt, SystemExit):
            cleanAndExit()
            

#***********************************************************#
class Timer:
    def __init__(self):
        self.start = 0.0
        self.end = 0.0
        self.timeElapsed = 0

#***********************************************************#

    def startTimer(self):
        self.start = int(time.time())
        
#***********************************************************#

    def endTimer(self):
        self.end = int(time.time())
        
#***********************************************************#

    def elapsedTime(self):
        self.endTimer()
        return (self.end - self.start)
        
#***********************************************************#

    def cleanTimer(self):
        self.start = 0
        self.end = 0
        
#***********************************************************#

def cleanAndExit():
    print ("Cleaning...")
    GPIO.cleanup()    
    print ("Bye!")
    sys.exit()
    
#***********************************************************#
    
def sendEmail(weight):
    email = Class_eMail()
    email.send_Text_Mail(EMAIL_ID, "[ALERT] Current weight is {} g".format(weight), "...")
    del email
    
#***********************************************************#
    
def calculateAverage(val):
    sum = 0.0
    length = 1
    avgWeight.append(val)
    if (len(avgWeight) < N_SAMPLES):
        return val
    del avgWeight[0]
    for num in avgWeight:
        sum = sum + num
    length = len(avgWeight)
    if (len(avgWeight) > 10):
        del avgWeight[:]
    return (sum/length)

#***********************************************************#

def main():
    weightS1 = 0.0
    alert1 = False
    alert2 = False
    emailSent = False
    timeElapsed = 0
    sensor1 = WeightSensor(DT1, SCK1)
    timer1 = Timer()
    sensor1.initializeGpio()
    while True:
        weightS1 = abs(calculateAverage(sensor1.getWeight()))
        if (alert1):
                timeElapsed = timer1.elapsedTime()
                if (not alert2 and timeElapsed >= TIME_LIMIT_L1 and weightS1 < MIN_WEIGHT):
                        timer1.cleanTimer()
                        timer1.startTimer()
                        alert2 = True
                        print ("Alert 2 activated")
        if (alert1 and alert2):
                timeElapsed = timer1.elapsedTime()
                print("Time elapsed 2 is {}".format(timeElapsed))
                if (timeElapsed >= TIME_LIMIT_L2 and weightS1 < MIN_WEIGHT):
                        if not emailSent:
                            print ("Sending alert email...")
                            sendEmail(round(weightS1, 1))
                            emailSent = True
        if (not alert1 and weightS1 < MIN_WEIGHT):
                timer1.startTimer()
                alert1 = True
                print ("Alert 1 activated")
        elif (alert1 and weightS1 > MIN_WEIGHT):
                timer1.cleanTimer()
                alert1 = False
                alert2 = False
                emailSent = False
        print ("sensor 1: {} g".format(round(weightS1, 1)))
        time.sleep(TIME_INTERVAL)
        
if __name__ == "__main__":
    main()
