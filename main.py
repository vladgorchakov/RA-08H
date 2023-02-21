import serial
from time import sleep


class JoinModeException(Exception):
    def __init__(self, join_mode):
        self.join_mode = join_mode

    def __str__(self):
        return f"Mode {self.join_mode} is not correct. Join mode must be OTAA or ABR."


class BaudrateException(Exception):
    def __init__(self, baudrate):
        self.baudrate = baudrate

    def __str__(self):
        return f"{self.baudrate} is invalid. Baudrate should not be more than 9600"

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
        request = self.send_command(at_command, 1)
        print(request)

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

    def read_baudrate(self):
        at_command = b"AT+CGBR?\r\n"
        request = self.send_command(at_command, 0.5)
        if request[2] == 'OK':
            return request[1][6:]

    def set_baudrate(self, baudrate):
        if baudrate > 9600:
            raise BaudrateException(baudrate)
        at_command = bytes(f"AT+CGBR={baudrate}\r\n".encode())
        self.uart.write(at_command)

    def read_join_mode(self):
        at_command = b"AT+CJOINMODE?\r\n"
        request = self.send_command(at_command, 0.5)
        if request[2] == 'OK':
            if request[1] == '+CJOINMODE:0':
                return 'OTAA'
            elif request[1] == '+CJOINMODE:1':
                return 'ABR'

    def set_join_mode(self, mode):
        if mode == 'OTTA':
            at_command = b"AT+CJOINMODE=0\r\n"
        elif mode == 'ABR':
            at_command = b"AT+CJOINMODE=1\r\n"
        else:
            raise JoinModeException(mode)

        request = self.send_command(at_command, 0.5)
        if request[1] == 'OK':
            return True

if __name__ == "__main__":
    ra = RA08H('COM7', 9600)
    print(ra.read_manufacturer_identification())
    print(ra.read_model_identification())
    print(ra.read_version_identification())
    print(ra.read_product_sequence_number())
    print(ra.read_join_mode())
    print(ra.set_join_mode('OTTA'))
    print(ra.read_baudrate())
    print(ra.read_manufacturer_identification())
