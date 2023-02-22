import serial
from time import sleep
from exceptions import *


class RA08H:
    def __init__(self, port, baudrate):
        self.uart = serial.Serial(port=port, baudrate=baudrate)

        # ABR SETTINGS
        self.__dev_addr_length = 8 # DevAddr length
        self.__apps_key_length = 32 # AppSKey length


    def connect(self):
        self.uart.open()
        if self.uart.is_open:
            print('Connection to RA08H-> OK')
            return True

    def send_command(self, command, timeout=1.0) -> list:
        self.uart.write(command)
        sleep(timeout)
        return self.uart.read_all().decode("utf-8").split("\r\n")

    def parse(self, request):
        if request[2] == 'OK':
            if ':' in request[1]:
                return request[1].split(':')[1]
            elif '=' in request[1]:
                return request[1].split('=')[1]

    def check_setting(self, request):
        print(request)
        if request[1] == 'OK':
            return True
        else:
            return False

    def check_parameter(self, value, correct_length, correct_mode):
        if len(value) == correct_length:
            if self.read_join_mode() == correct_mode:
                return True
            else:
                raise ABPJoinModeException
        else:
            raise SizeDevAddrException(len(value))

    def read_manufacturer_identification(self) -> dict:
        at_command = b"AT+CGMI?\r\n"
        return self.parse(self.send_command(at_command, 0.1))

    def read_model_identification(self):
        at_command = b"AT+CGMM?\r\n"
        return self.parse(self.send_command(at_command, 0.1))

    def read_version_identification(self):
        at_command = b"AT+CGMR?\r\n"
        return self.parse(self.send_command(at_command, 0.1))

    def read_product_sequence_number(self):
        at_command = b"AT+CGSN?\r\n"
        return self.parse(self.send_command(at_command, 0.1)[1:])

    def read_baudrate(self):
        at_command = b"AT+CGBR?\r\n"
        return self.parse(self.send_command(at_command, 0.1))

    def set_baudrate(self, baudrate):
        if baudrate > 9600:
            raise BaudrateException(baudrate)
        at_command = bytes(f"AT+CGBR={baudrate}\r\n".encode())
        self.uart.write(at_command)

    def read_join_mode(self):
        at_command = b"AT+CJOINMODE?\r\n"
        mode = self.parse(self.send_command(at_command, 0.1))
        if mode == '0':
            return 'OTAA'
        else:
            return 'ABP'

    def set_join_mode(self, mode):
        if mode == 'OTAA':
            at_command = b"AT+CJOINMODE=0\r\n"
        elif mode == 'ABP':
            at_command = b"AT+CJOINMODE=1\r\n"
        else:
            raise BaudrateException(mode)

        return self.check_setting(self.send_command(at_command, 0.5))

    def read_dev_eui(self):
        at_command = b"AT+CDEVEUI?\r\n"
        return self.parse(self.send_command(at_command, 0.5))

    def set_dev_eui(self, devEUI):
        at_command = bytes(f"AT+CDEVEUI={devEUI}\r\n".encode())
        return self.check_setting(self.send_command(at_command, 0.5))

    def read_app_eui(self):
        at_command = b"AT+CAPPEUI?\r\n"
        return self.parse(self.send_command(at_command, 0.5))

    def set_app_eui(self, app_eui):
        at_command = bytes(f"AT+CAPPEUI={app_eui}\r\n".encode())
        if self.read_join_mode() == "OTAA":
            return self.check_setting(self.send_command(at_command, 0.5))
        else:
            raise OTAAJoinModeException

    def read_app_key(self):
        at_command = b"AT+CAPPKEY?\r\n"
        return self.parse(self.send_command(at_command, 0.5))

    def set_app_key(self, app_key):
        at_command = bytes(f"AT+CAPPKEY={app_key}\r\n".encode())
        if self.read_join_mode() == "OTAA":
            return self.check_setting(self.send_command(at_command, 0.5))
        else:
            raise OTAAJoinModeException

    def read_dev_addr(self):
        at_command = b"AT+CDEVADDR?\r\n"
        return self.parse(self.send_command(at_command, 0.5))

    def set_dev_addr(self, addr):
        at_command = bytes(f"AT+CDEVADDR={addr}\r\n".encode())
        if self.check_parameter(value=addr, correct_length=self.__dev_addr_length, correct_mode="ABP"):
            return self.check_setting(self.send_command(at_command, 0.5))

    def read_apps_key(self):
        at_command = b"AT+CAPPSKEY?\r\n"
        return self.parse(self.send_command(at_command, 0.5))
