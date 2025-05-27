import serial
import serial.tools.list_ports
import time


def find_device():
    ports = list(serial.tools.list_ports.comports())
    # for port in ports:
    #     print(port.device)
    for port in ports:
        print(port)
        try:
            ser = serial.Serial(port.device, 115200, timeout=1, write_timeout=1)
            time.sleep(1)
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            response = send_gcodes(ser, ['IsDelta\r\n'])
            
            print(response)
            if response == 'YesDelta':
                print(f'Device found on {port.device}')
                return ser
            ser.close()
        except (serial.SerialException, OSError):
            continue
    raise Exception('Device not found')


def send_gcodes(ser, gcodes):
    for gcode in gcodes:
        try:
            ser.write(gcode.encode())
            #self.ser.readline()
            while True:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8').rstrip()
                    #print(line)
                    return line
        except serial.SerialTimeoutException:
            print("Timeout: Não foi possível escrever na serial no tempo definido.")
            return None
        
    
            
# device = serial.Serial('COM6', 115200, timeout=1)
# time.sleep(2)
# device.reset_input_buffer()
# device.reset_output_buffer()
# response = send_gcodes(device, ['IsDelta\r\n'])

# print(response)
device = find_device()
time.sleep(3)
device.close()
