import serial
import time
import re
from kelctl import KELSerial
from datetime import datetime
import sys
import glob

def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

devices = serial_ports()
dmm_port = ''
psu_port = ''
load_port = ''
bms_port = ''

print(devices)

for device in devices:
    time.sleep(1)

    temp_ser = serial.Serial(
        port=device,  # Replace with your serial port (e.g., 'COM1' on Windows)
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        xonxoff=True,  # Enable XON/XOFF flow control
        timeout=1
    )


    message = "*IDN?\n"
    temp_ser.write(message.encode())

    time.sleep(1)

    if temp_ser.in_waiting > 0:
        received_data = temp_ser.read(temp_ser.in_waiting).decode()
        #print(f"Received: {received_data.strip()}")
        if "1908" in received_data:
            dmm_port = device
        if "CPX400SP" in received_data:
            psu_port = device
        if "RS-KEL103" in received_data:
            load_port = device
        if "......" in received_data:
            bms_port = device
    else:
        print("No data received.")

    temp_ser.close()

if dmm_port != '':
    print("1908 DMM at serial port: " + dmm_port)
else:
    print("No DMM found")

if psu_port != '':
    print("CXP400SP PSU at serial port: " + psu_port)
else:
    print("No PSU found")

if load_port != '':
    print("Kel103 Loadbank at serial port: " + load_port)
else:
    print("No Loadbank found")

if bms_port != '':
    print("Battery BMS at serial port: " + bms_port)
else:
    print("No BMS found")

# Configure the serial port with XON/XOFF enabled
bms = serial.Serial(
    port=bms_port,  # Replace with your serial port (e.g., 'COM1' on Windows)
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    xonxoff=True,  # Enable XON/XOFF flow control
    timeout=1
)

cpx400 = serial.Serial(
    port=psu_port,  # Replace with your serial port (e.g., 'COM1' on Windows)
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    xonxoff=True,  # Enable XON/XOFF flow control
    timeout=1
)
cpx400.write("OP1 0\n".encode())

kel103 = KELSerial(load_port)
kel103.input.off()

DMM1908 = serial.Serial(
    port=dmm_port,  # Replace with your serial port (e.g., 'COM1' on Windows)
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    xonxoff=True,  # Enable XON/XOFF flow control
    timeout=1
)

DMM1908.write("VDC 100V\n".encode())
DMM1908.write("IDC2 10A\n".encode())

measurement_pattern = re.compile('^\\[(\\d{4}\\.\\d, ){11}(\\d{4}\\.\\d)\\] [+-]\\d{6}\\.\\d$')



def write_bms_line(s: str, filename, start, mode, psu_v, psu_i, load_v, load_i, dcc, dmm_v, dmm_i):
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
    with open(filename, "a") as bmsfile: # "time,elapsed,mode,PSU V,PSU I,Load V,Load I,mV1,mV2,mV3,mV4,mV5,mV6,mV7,mV8,mV9,mV10,mV11,mV12,mA,dcc,dmm_v,dmm_i\n"
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

        bmsfile.write(current + ',')
        bmsfile.write(dcc + ',')
        bmsfile.write(dmm_v + ',' + dmm_i)
        bmsfile.write("\n")

    return bms_stop

def dmm_read():
    global DMM1908

    DMM1908.write("Read?\n".encode())
    while DMM1908.in_waiting < 11:
        time.sleep(0.01)
    dmm_v = float(DMM1908.read(DMM1908.in_waiting).decode().strip().split(' ')[0])
    #print(received_data)

    DMM1908.write("Read2?\n".encode())
    while DMM1908.in_waiting < 11:
        time.sleep(0.01)
    dmm_i = float(DMM1908.read(DMM1908.in_waiting).decode().strip().split(' ')[0])
    #print(received_data)

    return dmm_v, dmm_i

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

        DMM1908.write("Read?\n".encode())

        dmm_reading = DMM1908.read(DMM1908.in_waiting).decode()

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
                [dmm_v, dmm_i] = dmm_read()
                stop_function = write_bms_line(msg.strip(), filename, ccd_start, mode, psu_v, psu_i, load_v, load_i,
                                               dcc, dmm_v, dmm_i)
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
                [dmm_v, dmm_i] = dmm_read()
                stop_function = write_bms_line(msg.strip(), filename, ccd_start, mode, psu_v, psu_i, load_v, load_i, dcc, dmm_v, dmm_i)
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
                [dmm_v, dmm_i] = dmm_read()
                stop_function = write_bms_line(msg.strip(), filename, ccd_start, mode, psu_v, psu_i, load_v, load_i,
                                               dcc, dmm_v, dmm_i)
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
filetime = datetime.now().strftime("%d%m%y_%H%M")
bms_filename = "./Data/Battery_Test_" + filetime + ".csv"
bms_file = open(bms_filename, "w")
bms_file.write("time,elapsed,mode,PSU V,PSU I,Load V,Load I,mV1,mV2,mV3,mV4,mV5,mV6,mV7,mV8,mV9,mV10,mV11,mV12,mA,dcc,dmm_v,dmm_i\n")
bms_file.close()

msg_in = bms.read(bms.in_waiting).decode().strip()
message = "s\n"
bms.write(message.encode())

v_max = 3650 #max Charge voltage
v_min = 2500 #Discharge cutoff voltage
v_nom = 3200 #nominal voltage

cell_lim_high = 3550
cell_lim_low = 2850

c_nom = 3.3 #intended capacity in Ah
mah_log = 3300

ccc_i = c_nom/2
ccd_i = c_nom/2

i_cont = c_nom*3 #continuous max current
i_puls = 10 #pulse max current 5s
i_end = 0.01*c_nom #current at the end of a CV charge

while(testing):

    time.sleep(0.9)

    if BMS_mainloop == 1:

        print("\nEntering CC discharge phase at C/2" + datetime.now().strftime("%H:%M:%S"))
        cc_discharge(c_nom/2,1, bms_filename)
        print("\nEntering CC discharge phase at C/4" + datetime.now().strftime("%H:%M:%S"))
        cc_discharge(c_nom/4,1, bms_filename)
        print("\nDone with CC discharge")

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

cxp

