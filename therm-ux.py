import glob
import time
import curses
#from curses import wrapper
from flask import Flask, send_from_directory
from flask import send_file
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv
import threading
from collections import OrderedDict


# Semaphore to enable logging to CSV file
tempLogEnable=0

# Constants
TEMP_POLL_INTERVAL=15  # seconds
TEMP_POLL_MAX=100000 # Max number of data points to collect
TEMP_CSV_FILE="temperature.csv"
TEMP_IMG_FILE="temperature.png"
TEMP_IMG_PATH="img/" + TEMP_IMG_FILE

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*') #[0]
#device_file = device_folder + '/w1_slave'
device_map = dict()
device_map["/sys/bus/w1/devices/28-00000ab375b7"] = "Shiny"
device_map["/sys/bus/w1/devices/28-000008714eb0"] = "Gimpy"

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
    if device in device_map:
        name = device_map[device]
        
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        #temp_f = temp_c * 9.0 / 5.0 + 32.0
        temp_f = ((float(temp_string) * 9.0) / 5.0) / 1000.0 + 32.0
        return temp_c, temp_f, name
#---------------------------------------------------

#---------------------------------------------------
# Return temperature data per probe as HTML string
def getTempHTMLStr():
    now = datetime.now()
    tempStr = now.strftime("%m/%d/%Y %H:%M:%S <br>")
    for d in device_folder:
        (c, f, name) = read_temp(d)
        buf = "[ %3.2f C ] [ %3.2f F ]  %s <br>" % (c, f, name)
        tempStr = tempStr + buf
    if tempLogEnable:
        tempStr = tempStr + '<a href="endplot" target="blank"><button>Stop Plot</button></a><br>'
        # Add a different string to the image url to force the browser not to cache the image, the string will be ignored otherwise
        tempStr = tempStr + '<img src="/img/temperature.png?' + str(time.time()) + '" alt="temperature plot">'
    else:
        tempStr = tempStr + '<a href="startplot" target="blank"><button>Start Plot</button></a><br>'
    return tempStr
#---------------------------------------------------

#---------------------------------------------------
# Given a time stamp input, save temperature data to the CSV file
def saveTempToCSV(t):
    tempStr = "%d, " % t
    for d in device_folder:
        (c, f, name) = read_temp(d)
        buf = "%s, %3.2f, " % (name, f)
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
    name1="" # probe1 name
    name2="" # probe2 name
    color1="red" # probe1 plot color
    color2="blue" # probe2 plot color
    with open(TEMP_CSV_FILE, 'r') as csvfile:
        plots= csv.reader(csvfile, delimiter=',')
        for row in plots:
            t.append(int(row[0]))
            name1=row[1]
            p1.append(float(row[2]))
            if len(row) > 4:
                name2=row[3]
                p2.append(float(row[4]))
    plt.plot(t, p1, color=color1, label=name1)
    if len(p2) > 0:
        plt.plot(t, p2, color=color2, label=name2)

    # This ridiculous code is needed to prevent labels from showing
    # up multiple times in the legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = OrderedDict(zip(labels, handles))
    #plt.legend(by_label.values(), by_label.keys(), loc="best")
    plt.legend(by_label.values(), by_label.keys(), 
               bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)

    plt.xlabel('Time')
    plt.ylabel('Temperature(F)')
    #plt.show()
    plt.savefig(TEMP_IMG_PATH)
    plt.clf()
    plt.cla()
    plt.close()
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
app = Flask(__name__, static_url_path='')

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

@app.route('/img/<path:filename>')
def send_img(filename):
    if filename == TEMP_IMG_FILE:
        savePlotImage()
    return send_from_directory('img', filename)

@app.route('/hello')
def hello():
    return "Hello World!"

# Run the Flask app             
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
    


