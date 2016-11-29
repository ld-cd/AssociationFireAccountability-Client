#!/usr/bin/python3
import requests
import time
import json
import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008

DS_DIFF = 2
ALARM_END_TIMEOUT = 600 # ten minutes (all times in this file are in seconds fyi)
SOUND_LEVEL = 860
AVERAGE_NUMBER = 75
#LIGHT_LEVEL = 1023
# The light sensor isn't reliable enough at this point.

token = '***REMOVED***'
server = 'http://associationfireaccountability.azurewebsites.net/api/hwmonitor/'
#server = 'http://localhost/api/hwmonitor/'

def send_data(fish, call, moose):
    r = requests.post(server + call, headers = {'Authentication' : moose, 'Content-Type' : 'application/json'}, data = json.dumps(fish))
    print(r.text)
    return r

def create_batch(moose):
    r = send_data({}, 'batch', moose)
    if r.status_code != 200:
        print(r.status_code)
        return -1
    parsed = json.loads(r)
    return parsed['BatchID']

def add_event(moose, eventtype, batchid, timestamp=int(time.time())):
    r = send_data({'Timestamp' : timestamp, 'Event' : eventtype, 'BatchID' : batchid}, 'alarm', moose)
    if r.status_code != 200:
        print(r.status_code)
        return -1
    parsed = json.loads(r)
    return parsed['EventID']

def average(mcp, channel, n):
    x = 0
    for i in range(1, n):
        t = mcp.read_adc(channel)
        if t == 0:
            t = 1023
        x += t
    return x / n

def detect_spike(mcp, channel, level):
    x = average(mcp, channel, AVERAGE_NUMBER)
    while x < level:
        x = average(mcp, channel, AVERAGE_NUMBER)
    print("spike")
    ss = time.time()
    while x > level:
        x = average(mcp, channel, AVERAGE_NUMBER)
        # possibly add a little bit of debounce here/lower sample rate
    return ss

def detect_double_spike(mcp, channel, level): # loop until we see a double spike (like a double flash but with less dead people [actually if the light works it will be a double flash ;-) ])
    last_spike = detect_spike(mcp, channel, level)
    while True:
        time.sleep(0.05)
        dis_spike = detect_spike(mcp, channel, level)
        if dis_spike - last_spike <= DS_DIFF:
            return [last_spike, dis_spike]
        last_spike = dis_spike

def detect_spike_timeout(mcp, channel, level, timeout):
    x = average(mcp, channel, AVERAGE_NUMBER)
    lst = time.time()
    while x < level:
        x = average(mcp, channel, AVERAGE_NUMBER)
        if time.time() - lst >= timeout:
            return -1
    ss = time.time()
    print("spike")
    while x > level:
        x = average(mcp, channel, AVERAGE_NUMBER)
    return ss

if __name__ == "__main__":
    mcp = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(0, 0))
    while True:
        dst = detect_double_spike(mcp, 0, SOUND_LEVEL) # https://xkcd.com/673/
        print("ALARM BEGINING")
        batchmoose = create_batch(token)
        add_event(token, "loudbeep", batchmoose, timestamp = dst[0])
        add_event(token, "loudbeep", batchmoose, timestamp = dst[1])
        print(dst[0])
        print(dst[1])
        while True:
            st = detect_spike_timeout(mcp, 0, SOUND_LEVEL, ALARM_END_TIMEOUT)
            if st == -1:
                break;
            print(st)
            add_event(token, "loudbeep", batchmoose, timestamp = int(st))
        print("ALARM ENDING AT" + str(time.time()))
        add_event(token, "end", batchmoose, timestamp = int(time.time())
