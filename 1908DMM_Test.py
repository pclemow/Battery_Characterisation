import serial
import time

# Configure the serial port with XON/XOFF enabled
DMM1908 = serial.Serial(
    port='COM8',  # Replace with your serial port (e.g., 'COM1' on Windows)
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    xonxoff=True,  # Enable XON/XOFF flow control
    timeout=1
)

DMM1908.write("VDC 30V\n".encode())
DMM1908.write("IDC2 10A\n".encode())

DMM1908.write("Read?\n".encode())
time.sleep(0.2)

received_data = DMM1908.read(DMM1908.in_waiting).decode()
print(f"Received: {received_data.strip()}")

DMM1908.close()
print("Serial port closed.")