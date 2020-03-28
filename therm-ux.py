import glob
import time
import curses
#from curses import wrapper
from flask import Flask
from flask import send_file
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv
import threading


# Semaphore to enable logging to CSV file
tempLogEnable=0

# Constants
TEMP_POLL_INTERVAL=15  # seconds
TEMP_POLL_MAX=100000 # Max number of data points to collect
TEMP_CSV_FILE="temperature.csv"
TEMP_IMG_FILE="temperature.png"

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*') #[0]
#device_file = device_folder + '/w1_slave'

#---------------------------------------------------
# Read raw temperature data
def read_temp_raw(device):
    device_file = device + '/w1_slave'
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
#---------------------------------------------------

#---------------------------------------------------
# Read temperature data, associate with temp probe device and return in array format
def read_temp(device):
    lines = read_temp_raw(device)
    name = device

    #substitute names
    if ( name == "/sys/bus/w1/devices/28-00000ab375b7" ):
        name = "Shiny"
    elif ( name == "/sys/bus/w1/devices/28-000008714eb0" ):
        name = "Gimpy"
        
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c, temp_f, name
#---------------------------------------------------

#---------------------------------------------------
# Return temperature data per probe as HTML string
def getTempHTMLStr():
    now = datetime.now()
    tempStr = now.strftime("%m/%d/%Y %H:%M:%S <br>")
    for d in device_folder:
        (c, f, name) = read_temp(d)
        buf = "[ %d C ] [ %d F ]  %s <br>" % (c, f, name)
        tempStr = tempStr + buf
    return tempStr
#---------------------------------------------------

#---------------------------------------------------
# Given a time stamp input, save temperature data to the CSV file
def saveTempToCSV(t):
    tempStr = "%d, " % t
    for d in device_folder:
        (c, f, name) = read_temp(d)
        buf = "%d, " % (f)
        tempStr = tempStr + buf
    tempStr = tempStr + "\n"
    f = open(TEMP_CSV_FILE,"a")
    f.write(tempStr)
    f.close()
#---------------------------------------------------

#---------------------------------------------------
# Create a new plot image file from the CSV data
def savePlotImage():
    t=[] # time stamp
    p1=[] # probe1 temperature (Fahrenheit)
    p2=[] # probe2 temperature (Fahrenheit)
    with open(TEMP_CSV_FILE, 'r') as csvfile:
        plots= csv.reader(csvfile, delimiter=',')
        for row in plots:
            t.append(int(row[0]))
            p1.append(int(row[1]))
            p2.append(int(row[2]))
    plt.plot(t, p1)
    plt.plot(t, p2)
    plt.xlabel('Time')
    plt.ylabel('Temperature')
    #plt.show()
    plt.savefig(TEMP_IMG_FILE)
#---------------------------------------------------


#---------------------------------------------------
# This thread is invoked to write the temperature plogs
# periodically to the CSV file.  The tempLogEnable semaphore 
# is used to start and stop the polling.
def tempLog():
    global tempLogEnable
    print ("Thread starting")
    while (1):
        while (tempLogEnable == 0): 
            time.sleep(1)
        print ("Thread enabled")
        # Create new empty file
        f = open(TEMP_CSV_FILE,"w+")
        f.close()
        # Reset time stamp
        t=0
        while ( (tempLogEnable == 1) and (t < TEMP_POLL_MAX) ):
            saveTempToCSV(t)
            t=t+1
            time.sleep(TEMP_POLL_INTERVAL)
        print ("Thread ending")
#---------------------------------------------------
    



# Start the tempLog thread
tempLog_thread = threading.Thread(target=tempLog)
tempLog_thread.start()


# Declare the Flask app             
app = Flask(__name__)

# Flask handlers
@app.route('/')
def index():
    return getTempHTMLStr()

@app.route('/startplot')
def startplot():
    global tempLogEnable
    tempLogEnable=1
    return "Plot started"

@app.route('/endplot')
def endplot():
    global tempLogEnable
    tempLogEnable=0
    return "Plot ended"

@app.route('/plot')
def plot():
    savePlotImage()
    #return "Image saved"
    return send_file(TEMP_IMG_FILE, mimetype='image/png')

@app.route('/hello')
def hello():
    return "Hello World!"

# Run the Flask app             
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
    


