from machine import UART
from time import sleep
from humidity import HumSensor
from cayenne import LPPcodec


class RA08H:
    def __init__(self, uart):
        self.uart = uart
        self.__is_join = False # Вернуть флаг
        self.__send_err_nums = {
            '00': 'Not Join Network success',
            '01': 'Communication path bush, data send fail',
            '02': 'Data length exceed the allowable length'
            }
        
    def send_command(self, command, size, time=9):
        self.uart.read()
        self.uart.write(command)
        i = 0
        while self.uart.any() < size and i < 90:
             print("char counter ->", self.uart.any())
             sleep(0.5)
             i += 1

        return self.uart.read().decode("utf-8").split("\n")

#     def parse(self, request):
#         if request[2] == 'OK':
#             if ':' in request[1]:
#                 return request[1].split(':')[1]
#             elif '=' in request[1]:
#                 return request[1].split('=')[1]
# 
#     def check_setting(self, request):
#         print(request)
#         if request[1] == 'OK':
#             return True
#         else:
#             return False
    
    def join(self):
        at = "AT+CJOIN=1,0,0,1\r"
        self.uart.write(at)
        sleep(10)
        print("char counter ->", self.uart.any())
        
        size = self.uart.any()
        if size == 159:
            self.__is_join = False
            self.uart.read()
            return False, {"STATUS": "CJOIN:FAIL", "MSG": "not joined"}
        elif size == 132 or size == 148:
            self.__is_join = True
            self.uart.read()
            return True, {"STATUS": "CJOIN:OK", "MSG": "joined"}
        else:
            return False, {"STATUS": "CJOIN:FAIL", "MSG": "not joined"}
    
    def check_send(self, log, response):
        try:
            if "OK+SEND:" in response[1]:
                log['SEND'] = {'STATUS': 'OK+SEND', 'TX_LEN': response[1][8:-1]}
                return True
            elif "ERR+SEND:" in response[1]:
                err_num = response[1][9:-1]
                if err_num in self.__send_err_nums.keys():
                    log['SEND'] = {'STATUS': 'ERR+SEND', 'ERR_NUM': (err_num, self.__send_err_nums[err_num])}
                else:
                    log['SEND'] = {'STATUS': 'ERR+SEND', 'ERR_NUM': (err_num, 'Unknown')}
                return False
        except:
            return False
            
    def check_sent(self, log, response):
        try:
            if "OK+SENT:" in response[6]:
                log['SENT'] = {'STATUS': 'OK+SENT', 'TX_CNT': response[6][8:-1]}
                return True
            elif "ERR+SENT:" in response[6]:
                log['SENT'] = {'STATUS': 'ERR+SENT', 'TX_CNT': response[6][9:-1]}
                return False
        except:
            return False
    
    def check_recv(self, log, response):
        try:
            if "OK+RECV:" in response[10]:
                data = response[10][8:-1].split(',')
                log['RECV'] = {'STATUS': "OK+RECV", "TYPE": data[0], "PORT": data[1], "LEN": data[2]}
                return True
            else:
                return False
        except:
            return False
    
    
    def send_data(self, data):
        log = {}
        data_size = int(len(data) / 2)
        at = "AT+DTRX=1,2," + str(data_size) + "," + data + "\r"
        print("AT -> " + at)
        response = self.send_command(at, 190)
        print(response)
        try:
            rd = response[-5].split(':')[1].split(',')
        except IndexError:
            print('correct response -> no')
            return False, log
        else:    
            if not self.check_send(log, response):
                return False, log
            
            elif not self.check_sent(log, response):
                return False, log
            
            elif not self.check_recv(log, response):
                return False, log
            
            else:
                log['freq'] = {
                    "tx_freq": int(response[3][22:31]),
                    "rx_freq": int(response[4][12:21])
                    }
                    
                log["received_data"] = {
                    "rssi": rd[0][8:],
                    "snr": rd[1][7:],
                    "daterate": rd[2][12:-1]
                    }
        
            return True, log
    
    
    def set_date_rate(self, dr = 3):
        self.uart.write("AT+CADR=0\r")
        sleep(1)
        print(self.uart.read())
        self.uart.write("AT+CDATARATE=" + str(dr) + "\r")
        sleep(3)
        print(self.uart.read())
        
    def set_tx_power(self, power):
        self.uart.write("AT+CTXP=" + str(power) + "\r")
        sleep(1)
        print(self.uart.read())
        
        
    @property
    def is_join(self):
        return self.__is_join
