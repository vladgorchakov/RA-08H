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
            return {'status': request[2], 'manufacter': request[1][6:]}
        else:
            return {'status': 'error'}


if __name__ == "__main__":
    ra = RA08H('COM7', 9600)
    print(ra.read_manufacturer_identification())
