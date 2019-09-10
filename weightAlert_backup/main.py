#! /usr/bin/python2
#  main program for weight measuring (hx711) and handling email communication (smtp and imap)
#  author: Karol Siegieda

import time
import os
import sys
import inspect
import datetime
import ConfigParser
from email_handler import Class_eMail

import RPi.GPIO as GPIO
from hx711 import HX711

# Add dictionary
dictionaryDir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
dictionaryFilePath =  os.path.join(dictionaryDir, 'dictionary.ini')

N_SAMPLES = 5
TIME_INTERVAL = 1
REFERENCE = -435
TIME_LIMIT = 4
MIN_WEIGHT = 100
REPORT_TIME = 22
# sensor 1
SNAME1 = "upper"
DT1 = 25
SCK1 = 18
# sensor 2
SNAME2 = "middle"
DT2 = 5
SCK2 = 6
sensorList = []
#***********************************************************#
class WeightSensor:
    def __init__(self, dt, sck):
        self.name = ""
        self.itemsSold = 0
        self.itemsLeft = 0
        self.hx = None
        self.dt = dt
        self.sck = sck
        self.timer = Timer()
        self.avgWeight = []
        self.alertPrimary = False
        self.alertSecondary = False
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

    def calculateAverage(self, val):
        length = 1
        self.avgWeight.append(val)
        if (len(self.avgWeight) < N_SAMPLES):
            return val
        del self.avgWeight[0]
        if (len(self.avgWeight) > 10):
            del self.avgWeight[:]

#***********************************************************#

    def getAverageWeight(self):
        sum = 0.0
        for num in self.avgWeight:
            sum = sum + num
        length = len(self.avgWeight)
        return (sum/length)

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

def sendEmail(sensor):
    email = Class_eMail()
    email.send_Text_Mail("[ALERT] Current weight on {} is {} g".format(sensor.name, sensor.getAverageWeight()), "...")
    del email

#***********************************************************#

def readDictionary():
    try:
        config = ConfigParser.ConfigParser()
        config.optionxform=str   #By default config returns keys from Settings file in lower case. This line preserves the case for keys
        config.read(dictionaryFilePath)

        global DICT_DAY
        global DICT_SOLD
        global DICT_IN_STOCK
        global DICT_SENSOR_UP
        global DICT_SENSOR_MIDDLE
        global DICT_SENSOR_DOWN
        
        DICT_DAY = config.get("DICTIONARY","DICT_DAY")
        DICT_SOLD = config.get("DICTIONARY","DICT_SOLD")
        DICT_IN_STOCK = config.get("DICTIONARY","DICT_IN_STOCK")
        DICT_REPORT_FROM = config.get("DICTIONARY","DICT_REPORT_FROM")
        DICT_SENSOR_UP = config.get("DICTIONARY","DICT_SENSOR_UP")
        DICT_SENSOR_MIDDLE = config.get("DICTIONARY","DICT_SENSOR_MIDDLE")
        DICT_SENSOR_DOWN = config.get("DICTIONARY","DICT_SENSOR_DOWN")

    except Exception as error_msg:
        print "Error while trying to read dictionary."
        print {"Error" : str(error_msg)}

#***********************************************************#

def getCurrentHour():
    now = datetime.datetime.now()
    return now.strftime("%H")

#***********************************************************#

def getCurrentDay():
    day = datetime.datetime.now()
    return day.strftime("%Y-%m-%d")

#***********************************************************#
def checkReportTime():
    if (int(getCurrentHour()) == REPORT_TIME):
        return True
    else:
        return False

#***********************************************************#

def sendDailyReport():
    print ("Sending daily report")
    raportMsg = "{}:  {} \n\n".format(DICT_DAY, getCurrentDay())
    for sensor in sensorList:
        raportMsg += "{}\n".format(sensor.name)
        raportMsg += "\t{}:  {}\n".format(DICT_SOLD, sensor.itemsSold)
        raportMsg += "\t{}:  {}\n\n".format(DICT_IN_STOCK, sensor.itemsLeft)
    email = Class_eMail()
    email.send_Text_Mail("{} {}".format(DICT_REPORT_FROM, getCurrentDay()), raportMsg)
    
#***********************************************************#

def main():
    readDictionary()
    emailSent = False
    # initialize sensor 1
    sensor1 = WeightSensor(DT1, SCK1)
    sensor1.initializeGpio()
    sensor1.name = DICT_SENSOR_UP
    sensorList.append(sensor1)
    # initialize sensor 2
    sensor2 = WeightSensor(DT2, SCK2)
    sensor2.initializeGpio()
    sensor2.name = DICT_SENSOR_MIDDLE
    sensorList.append(sensor2)
    while True:
        #weightS1 = abs(calculateAverage(sensor1.getWeight(), avgWeight1))
        #weightS2 = abs(calculateAverage(sensor2.getWeight(), avgWeight2))
        for sensor in sensorList:
            sensor.calculateAverage(sensor.getWeight())
            if (sensor.getAverageWeight() < MIN_WEIGHT):
                sensor.timer.cleanTimer()
                sensor.timer.startTimer()
            sensor.alertSecondary = True
            if (sensor.alertSecondary):
                timeElapsed = sensor.timer.elapsedTime()
#                if (timeElapsed >= TIME_LIMIT and weightS1 < MIN_WEIGHT):
#                        if not emailSent:
#                            print ("Sending alert email...")
#                            sendEmail(round(weightS1, 1))
#                            emailSent = True
#        if (not alert and weightS1 < MIN_WEIGHT):
#                timer1.startTimer()
#                alert1 = True
#                print ("Alert 1 activated")
#        elif (alert1 and weightS1 > MIN_WEIGHT):
#                timer1.cleanTimer()
#                alert1 = False
#                alert2 = False
#                emailSent = False
            print ("sensor [{}]: {} g".format(sensor.name, round(sensor.getAverageWeight(), 1)))
        print ("hour is {}".format(getCurrentHour()))
        if (checkReportTime()):
            sendDailyReport()
        time.sleep(TIME_INTERVAL)

if __name__ == "__main__":
    main()
