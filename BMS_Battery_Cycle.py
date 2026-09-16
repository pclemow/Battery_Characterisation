import serial
import time
import re
from kelctl import KELSerial
from datetime import datetime

# Configure the serial port with XON/XOFF enabled
bms = serial.Serial(
    port='COM15',  # Replace with your serial port (e.g., 'COM1' on Windows)
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    xonxoff=True,  # Enable XON/XOFF flow control
    timeout=1
)

cpx400 = serial.Serial(
    port='COM3',  # Replace with your serial port (e.g., 'COM1' on Windows)
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    xonxoff=True,  # Enable XON/XOFF flow control
    timeout=1
)
cpx400.write("OP1 0\n".encode())

kel103 = KELSerial('COM5')
kel103.input.off()

measurement_pattern = re.compile('^\\[(\\d{4}\\.\\d, ){11}(\\d{4}\\.\\d)\\] [+-]\\d{6}\\.\\d$')

v_max = 3650 #max Charge voltage
v_min = 2500 #Discharge cutoff voltage
v_nom = 3200 #nominal voltage

cell_lim_high = 3550
cell_lim_low = 2850

c_nom = 3.3 #intended capacity in Ah
mah_log = 3300

ccc_i = c_nom
ccd_i = c_nom

i_cont = c_nom*3 #continuous max current
i_puls = 10 #pulse max current 5s
i_end = 0.01*c_nom #current at the end of a CV charge

def write_bms_line(s: str, filename, start, mode, psu_v, psu_i, load_v, load_i):
    global cell_lim_high, cell_lim_low
    # Split into the list part and the current part
    list_part, current_part = s.split("]")
    bms_stop = 0
    #print(list_part)
    # Parse the 12 cell voltages
    list_part = list_part.strip()[1:]  # remove leading '['
    cell_voltages = list_part.split(",")

    # Parse the current
    current = current_part.strip()

    # Write to CSV
    cell_count = 1
    with open(filename, "a") as bmsfile: # "time,elapsed,mode,PSU V,PSU I,Load V,Load I,mV1,mV2,mV3,mV4,mV5,mV6,mV7,mV8,mV9,mV10,mV11,mV12,mA\n"
        timenow = datetime.now().strftime("%H:%M:%S")

        elapsed_seconds = int((datetime.now() - start).total_seconds())

        bmsfile.write(timenow + ',' + str(elapsed_seconds) + ',' + mode + ',' + psu_v + ',' + psu_i + ',' + load_v + ',' + load_i + ',')
        for voltage in cell_voltages:
            bmsfile.write(voltage)
            bmsfile.write(",")
            cell_count += 1
            if float(voltage) > cell_lim_high:
                bms_stop += 2 ** (cell_count - 1)
            elif float(voltage) < cell_lim_low:
                bms_stop += 2 ** (cell_count - 1)

        bmsfile.write(current)
        bmsfile.write("\n")

    return bms_stop

def cccv_charge(ccc_iset, balancing, filename):
    ccc_start = datetime.now()
    mode = "CC Charge"
    psu_v = str(cell_lim_high * 12 / 1000)
    psu_i = str(ccc_iset)
    load_v = "0"
    load_i = "0"
    stop_function = 0
    bal_count = 0
    dcc = 0

    cpx400.write(("I1 {}\n".format(ccc_iset)).encode())  # current limit to 1C
    cpx400.write(("V1 {}\n".format(cell_lim_high * 12 / 1000)).encode())  # voltage setting to Vmax
    cpx400.write("OP1 1\n".encode())  # enable output

    while stop_function == 0:
        ccc_message = "m\n"
        bms.write(ccc_message.encode())
        time.sleep(1)
        if bms.in_waiting > 0:
            ccc_msg_in = bms.read(bms.in_waiting).decode()
            msg = ccc_msg_in.strip().split("\r\n")[0]
            if measurement_pattern.match(msg):
                print("\r" + msg, end="")
                if balancing == 1:
                    if bal_count == 28:
                        dcc = 0
                        bms.write(("dcc {}\n".format(dcc)).encode())
                    if bal_count > 29:
                        dcc = bms_balancing(msg.strip())
                        bms.write(("dcc {}\n".format(dcc)).encode())
                        bal_count = 0
                    print(" {}".format(dcc), end="")
                stop_function = write_bms_line(msg.strip(), filename, ccc_start, mode, psu_v, psu_i, load_v, load_i)
            elif "Ready" in msg_in:
                stop_function = 0
                # print(msg_in)
            else:
                print(msg_in)
                stop_function = 1
        bal_count += 1

    cpx400.write("OP1 0\n".encode())  # turn off psu output

def cc_discharge(ccd_iset, balancing, filename):

    ccd_start = datetime.now()
    mode = "CC Discharge"
    psu_v = "0"
    psu_i = "0"
    load_v = "0"
    load_i = str(ccd_iset)

    kel103.current = ccd_iset
    kel103.input.on()
    stop_function = 0
    bal_count = 0
    dcc = 0

    while stop_function == 0:
        ccd_message = "m\n"
        bms.write(ccd_message.encode())
        time.sleep(1)
        if bms.in_waiting > 0:
            ccd_msg_in = bms.read(bms.in_waiting).decode()
            msg = ccd_msg_in.strip().split("\r\n")[0]
            if measurement_pattern.match(msg):
                print("\r" + msg, end="")
                if balancing == 1:
                    if bal_count == 28:
                        dcc = 0
                        bms.write(("dcc {}\n".format(dcc)).encode())
                    if bal_count > 29:
                        dcc = bms_balancing(msg.strip())
                        bms.write(("dcc {}\n".format(dcc)).encode())
                        bal_count = 0
                    print(" {}".format(dcc), end="")
                stop_function = write_bms_line(msg.strip(), filename, ccd_start, mode, psu_v, psu_i, load_v, load_i)
            elif "Ready" in msg_in:
                #print(msg_in)
                stop_function = 0
            else:
                print(msg_in)
                stop_function = 1
        bal_count += 1

    kel103.input.off()

def rest_battery(rest_time, balancing, filename):
    rest_start = datetime.now()
    mode = "Rest Battery"
    psu_v = "0"
    psu_i = "0"
    load_v = "0"
    load_i = "0"

    rest_count = 0
    bal_count = 0
    dcc = 0

    while rest_count < rest_time:
        rest_message = "m\n"
        bms.write(rest_message.encode())
        time.sleep(1)
        if bms.in_waiting > 0:
            rest_msg_in = bms.read(bms.in_waiting).decode()
            msg = rest_msg_in.strip().split("\r\n")[0]
            if measurement_pattern.match(msg):
                print("\r" + msg, end="")
                if balancing == 1:
                    if bal_count == 28:
                        dcc = 0
                        bms.write(("dcc {}\n".format(dcc)).encode())
                    if bal_count > 29:
                        dcc = bms_balancing(msg.strip())
                        bms.write(("dcc {}\n".format(dcc)).encode())
                        bal_count = 0
                    print(" {}".format(dcc), end="")
                stop_function = write_bms_line(msg.strip(), filename, rest_start, mode, psu_v, psu_i, load_v, load_i)
            elif "Ready" in msg_in:
                stop_function = 0
                # print(msg_in)
            else:
                print(msg_in)
        rest_count += 1
        bal_count += 1

def bms_balancing(s: str):
    # Split into the list part and the current part
    list_part, current_part = s.split("]")

    #print(list_part)
    # Parse the 12 cell voltages
    list_part = list_part.strip()[1:]  # remove leading '['
    cell_voltages = list_part.split(",")

    # Parse the current
    current = current_part.strip()

    min_cell = 5000

    for voltage in cell_voltages:
        if float(voltage) < min_cell:
            min_cell = float(voltage)

    bal_limit = min_cell + 50 # 50mV hysteresis

    dcc_count = 0
    dcc_out = 0

    for voltage in cell_voltages:
        if float(voltage) >  bal_limit:
            dcc_out = dcc_out + (2 ** dcc_count)
        dcc_count += 1

    return dcc_out


BMS_mainloop = 0
testing = 1

bms_filename = "./Data/bms_rest_bal.csv"
bms_file = open(bms_filename, "w")
bms_file.write("time,elapsed,mode,PSU V,PSU I,Load V,Load I,mV1,mV2,mV3,mV4,mV5,mV6,mV7,mV8,mV9,mV10,mV11,mV12,mA\n")
bms_file.close()

msg_in = bms.read(bms.in_waiting).decode().strip()
message = "s\n"
bms.write(message.encode())

while(testing):

    time.sleep(0.9)

    if BMS_mainloop == 1:

        #print("Entering CC charge phase")
        #cccv_charge(ccc_i,1, bms_filename)
        #print("\nDone with CC charge")
        print("Resting")
        rest_battery(1800,1, bms_filename)
        #print("\nEntering CC discharge phase")
        #cc_discharge(ccd_i,1, bms_filename)
        #print("\nDone with CC discharge")

        testing = 0

    else:
        if bms.in_waiting > 0:
            msg_in = bms.read(bms.in_waiting).decode().strip()
            if "Starting BMS Loop" in msg_in:
                print("Detected loop start")
                BMS_mainloop = 1
            else:
                print(msg_in)

message = "p\n"
bms.write(message.encode())