import serial
from time import sleep


class RA08H:
    def __init__(self, port, baudrate):
        self.uart = serial.Serial(port=port, baudrate=baudrate)

    def connect(self):
        self.uart.open()
        if self.uart.is_open:
            print('Connection to RA08H-> OK')
            return True

    def send_command(self, command, timeout=1.0) -> list:
        self.uart.write(command)
        sleep(timeout)
        return self.uart.read_all().decode("utf-8").split("\r\n")

    def read_manufacturer_identification(self) -> dict:
        at_command = b"AT+CGMI?\r\n"
        request = self.send_command(at_command, 0.5)

        if request[2] == 'OK':
            return {'status': request[2], 'manufacturer': request[1][6:]}
        else:
            return {'status': 'error'}

    def read_model_identification(self):
        at_command = b"AT+CGMM?\r\n"
        request = self.send_command(at_command, 0.5)
        if request[2] == 'OK':
            return {'status': request[2], 'model': request[1][6:]}
        else:
            return {'status': 'error'}

    def read_version_identification(self):
        at_command = b"AT+CGMR?\r\n"
        request = self.send_command(at_command, 0.5)
        if request[2] == 'OK':
            return {'status': request[2], 'version': request[1][6:]}
        else:
            return {'status': 'error'}

    def read_product_sequence_number(self):
        at_command = b"AT+CGSN?\r\n"
        request = self.send_command(at_command, 0.5)
        if request[2] == 'OK':
            return {'status': request[2], 'sn': request[1][6:]}
        else:
            return {'status': 'error'}

    def read_join_mode(self):
        at_command = b"AT+CJOINMODE?\r\n"
        request = self.send_command(at_command, 0.5)
        print(request)
        if request[2] == 'OK':
            if request[1] == '+CJOINMODE:0':
                return 'OTAA'
            elif request[1] == '+CJOINMODE:1':
                return 'ABR'

if __name__ == "__main__":
    ra = RA08H('COM7', 9600)
    print(ra.read_manufacturer_identification())
    print(ra.read_model_identification())
    print(ra.read_version_identification())
    print(ra.read_product_sequence_number())
    print(ra.read_join_mode())