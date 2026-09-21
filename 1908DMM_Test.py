import serial
import time
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
DMM1908 = serial.Serial(
    port=dmm_port,  # Replace with your serial port (e.g., 'COM1' on Windows)
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    xonxoff=True,  # Enable XON/XOFF flow control
    timeout=1
)

DMM1908.write("VDC 10V\n".encode())
DMM1908.write("IDC2 10A\n".encode())

DMM1908.write("Read?\n".encode())
while DMM1908.in_waiting < 11:
    time.sleep(0.01)
received_data = float(DMM1908.read(DMM1908.in_waiting).decode().strip().split(' ')[0])
print(received_data)

DMM1908.write("Read2?\n".encode())
while DMM1908.in_waiting < 11:
    time.sleep(0.01)
received_data = float(DMM1908.read(DMM1908.in_waiting).decode().strip().split(' ')[0])
print(received_data)

DMM1908.close()
print("Serial port closed.")
