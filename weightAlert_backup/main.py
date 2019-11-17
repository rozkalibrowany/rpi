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
TIME_INTERVAL = 0.5
TIME_SLEEP_LONG = 3600
TIME_ANALYSING = 2
TIME_ALERT_LIMIT = 3
REFERENCE = -435
DEF_WEIGHT = 0
UNIT_WEIGHT = 100
MIN_WEIGHT = 100
WEIGHT_TOLERANCE = 10
OPENING_TIME = 8
CLOSING_TIME = 18
TIME_HOUR_FORMAT = "%H"
TIME_FULL_FORMAT = "%H:%M"
dailyReportSent = False
# sensor 1
DT1 = 25
SCK1 = 18
# sensor 2
DT2 = 5
SCK2 = 6
# sensor 3
DT2 = 5
SCK2 = 6
sensorList = []

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
class WeightSensor:
    def __init__(self, dt, sck):
        self.name = ""
        self.itemsSold = 0
        self.itemsAdded = 0
        self.itemsLeft = 0
        self.hx = None
        self.dt = dt
        self.sck = sck
        self.timer = Timer()
        self.tempWeight = 0
        self.savedWeight = 0
        self.diff = 0
        self.cnt = 0
        self.avgWeight = []
        self.analysing = False
        self.lowWeightAlert = False
        
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

    def reset(self):
        self.itemsSold = 0

#***********************************************************#

    def getWeight(self):
        try:
            val = self.hx.get_weight(5)
            self.hx.power_down()
            self.hx.power_up()
            if (val <= WEIGHT_TOLERANCE):
                return 0
            return (int(val))
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
        sum = 0
        for num in self.avgWeight:
            sum = sum + num
        length = len(self.avgWeight)
        if (length == 0):
            return 0
        return int(abs((sum/length)))
    
#***********************************************************#

    def substraction(self, val1, val2):
        return (val1 - val2)
        
#***********************************************************#
    
    def calculateDiff(self, weight):
        return int(weight/UNIT_WEIGHT)

#***********************************************************#

    def isItemTakeOff(self, val):
        if (val > 0):
            return True
        else:
            return False
        
#***********************************************************#

    def setItemsQuantity(self, items, added):
        if (added):
            print ("\t {}: {} itemy".format(DICT_ADDED, items))
            self.itemsLeft += items
            self.itemsAdded += items
        else:
            print ("\t {}: {} itemy".format(DICT_TAKE_OFF, items))
            self.itemsLeft -= items
            self.itemsSold += items

#***********************************************************#

def cleanAndExit():
    print ("Cleaning...")
    GPIO.cleanup()
    print ("Bye!")
    sys.exit()

#***********************************************************#

def sendAlertEmail(sensor, weight):
    header = "[{}] {} - {} ({}g)".format(getCurrentTime(TIME_FULL_FORMAT), sensor.name, DICT_STOCK_EMPTY, weight)
    print ("Sending email(" + header + ")")
    email = Class_eMail()
    email.send_Text_Mail(header, "")
    del email

#***********************************************************#

def onChangeItemEmail(name, items, weight, added):
    header = "[{}] {} - ".format(getCurrentTime(TIME_FULL_FORMAT), name) 
    if (added == True):
        header += DICT_ADDED
    else:
        header += DICT_TAKE_OFF
    header += " {} {} ({}g)".format(items, DICT_ITEM, weight)
    print ("Sending email(" + header + ")")
    email = Class_eMail()
    email.send_Text_Mail(header, "")
    del email
    
#***********************************************************#

def sendDailyReport():
    print ("Sending daily report...")
    raportMsg = "{}:  {} \n\n".format(DICT_DAY, getCurrentDay())
    for sensor in sensorList:
        raportMsg += "{}\n".format(sensor.name)
        raportMsg += "\t{}:  {}\n".format(DICT_SOLD, sensor.itemsSold)
        raportMsg += "\t{}:  {}\n".format(DICT_IN_STOCK, sensor.itemsLeft)
    raportMsg += "\n{}:  {}".format(DICT_REPORT_TIME, getCurrentTime(TIME_FULL_FORMAT))
    email = Class_eMail()
    email.send_Text_Mail("{} {}".format(DICT_REPORT_FROM, getCurrentDay()), raportMsg)
    print ("Daily report sent")

#***********************************************************#

def readDictionary():
    try:
        config = ConfigParser.ConfigParser()
        config.optionxform=str   #By default config returns keys from Settings file in lower case. This line preserves the case for keys
        config.read(dictionaryFilePath)

        global DICT_DAY
        global DICT_SOLD
        global DICT_IN_STOCK
        global DICT_REPORT_FROM
        global DICT_SENSOR_UP
        global DICT_SENSOR_MIDDLE
        global DICT_SENSOR_DOWN
        global DICT_REPORT_TIME
        global DICT_TAKE_OFF
        global DICT_STOCK_EMPTY
        global DICT_ADDED
        global DICT_ITEM
        global DICT_CHANGE
        global DICT_AT_TIME
        
        DICT_DAY = config.get("DICTIONARY","DICT_DAY")
        DICT_SOLD = config.get("DICTIONARY","DICT_SOLD")
        DICT_IN_STOCK = config.get("DICTIONARY","DICT_IN_STOCK")
        DICT_REPORT_FROM = config.get("DICTIONARY","DICT_REPORT_FROM")
        DICT_SENSOR_UP = config.get("DICTIONARY","DICT_SENSOR_UP")
        DICT_SENSOR_MIDDLE = config.get("DICTIONARY","DICT_SENSOR_MIDDLE")
        DICT_SENSOR_DOWN = config.get("DICTIONARY","DICT_SENSOR_DOWN")
        DICT_REPORT_TIME = config.get("DICTIONARY","DICT_REPORT_TIME")
        DICT_TAKE_OFF = config.get("DICTIONARY", "DICT_TAKE_OFF")
        DICT_STOCK_EMPTY = config.get("DICTIONARY", "DICT_STOCK_EMPTY")
        DICT_ADDED = config.get("DICTIONARY", "DICT_ADDED")
        DICT_ITEM = config.get("DICTIONARY", "DICT_ITEM")
        DICT_CHANGE = config.get("DICTIONARY", "DICT_CHANGE")
        DICT_AT_TIME = config.get("DICTIONARY", "DICT_AT_TIME")

    except Exception as error_msg:
        print "Error while trying to read dictionary."
        print {"Error" : str(error_msg)}

#***********************************************************#

def getCurrentTime(format):
    now = datetime.datetime.now()
    return now.strftime(format)

#***********************************************************#

def getCurrentDay():
    day = datetime.datetime.now()
    return day.strftime("%Y-%m-%d")

#***********************************************************#
def getReportTime():
    if (int(getCurrentTime(TIME_HOUR_FORMAT)) == CLOSING_TIME):
        return True
    else:
        return False

#***********************************************************#

def areWorkingHours(time):
    time = int(time)
    if ((time >= int(OPENING_TIME) and time <= int(CLOSING_TIME))):
        return True
    else:
        return False
    
#***********************************************************#
#getCurrentTime(TIME_HOUR_FORMAT)
def main():
    global dailyReportSent
    if not areWorkingHours(17):
        print ("Current time {}".format(getCurrentTime(TIME_HOUR_FORMAT)))
        print ("Shop closed, going to sleep...")
        if (dailyReportSent == False):
            sendDailyReport()
            dailyReportSent = True
        time.sleep(TIME_SLEEP_LONG)
    elif (getCurrentTime(TIME_HOUR_FORMAT) == OPENING_TIME):
        dailyReportSent = False
        sensor.lowWeightAlert = False
    for sensor in sensorList:
        time.sleep(0.5)
        print ("sensor [{}]: {} g".format(sensor.name, round(sensor.getWeight(), 1)))
        print ("tempWeight: {}".format(sensor.tempWeight))
        print ("savedWeight: {}".format(sensor.savedWeight))
        print ("sensor.diff {} ".format(abs(sensor.diff)))
        print ("sensor.cnt {} ".format(sensor.cnt))
        #if (sensor.getWeight() < int(MIN_WEIGHT)):
        #    sensor.tempWeight = 0
        #    continue'''
        weight = sensor.getWeight()
        tempDiff = abs(int(sensor.substraction(weight, sensor.tempWeight)))
        print ("tempDiff {} ".format(abs(tempDiff)))
        if (tempDiff < int(UNIT_WEIGHT)):
            sensor.tempWeight = weight
            time.sleep(0.05)
        else:
            sensor.savedWeight = weight
        if (sensor.savedWeight > int(UNIT_WEIGHT) or tempDiff > int(UNIT_WEIGHT)):
            #sensor.savedWeight = sensor.tempWeight
            sensor.cnt += 1
        if (sensor.cnt > N_SAMPLES and tempDiff < int(UNIT_WEIGHT)):
            sensor.cnt = 0
        if (abs(tempDiff) > int(UNIT_WEIGHT) and sensor.cnt > N_SAMPLES):
            if (sensor.analysing == False):
                print ("STARTED ANALYSING")
                sensor.analysing = True
                sensor.timer.cleanTimer()
                sensor.timer.startTimer()
                sensor.diff = tempDiff
        elif (sensor.cnt > N_SAMPLES):
            if (abs(sensor.substraction(sensor.getWeight(), sensor.savedWeight) < UNIT_WEIGHT)):
                sensor.cnt = 0
                sensor.diff = 0
            else:
                sensor.cnt = 0
                sensor.savedWeight = 0
        if (sensor.analysing == True and sensor.timer.elapsedTime() > TIME_ALERT_LIMIT):
            diff = int(sensor.substraction(sensor.getWeight(), sensor.tempWeight))
            if (abs(diff) > UNIT_WEIGHT):
                onChangeItemEmail(sensor.name, sensor.calculateDiff(abs(diff)), abs(diff), sensor.isItemTakeOff(diff))
            sensor.tempWeight = sensor.getWeight()
            if (sensor.tempWeight < int(UNIT_WEIGHT) and sensor.lowWeightAlert == False):
                sendAlertEmail(sensor, sensor.tempWeight)
            sensor.analysing = False
            sensor.timer.cleanTimer()
        #else:
        #    sensor.currentWeight = int(sensor.getWeight())
if __name__ == "__main__":
    readDictionary()
    emailSent = False
    # initialize sensor 1
    sensor1 = WeightSensor(DT1, SCK1)
    sensor1.initializeGpio()
    sensor1.name = DICT_SENSOR_UP
    sensorList.append(sensor1)
    # initialize sensor 2
    #sensor2 = WeightSensor(DT2, SCK2)
    #sensor2.initializeGpio()
    #sensor2.name = DICT_SENSOR_MIDDLE
    #sensorList.append(sensor2)
    # initialize sensor 3
    #sensor3 = WeightSensor(DT2, SCK2)
    #sensor3.initializeGpio()
    #sensor3.name = DICT_SENSOR_DOWN
    #sensorList.append(sensor3)
    while True:
        main()

