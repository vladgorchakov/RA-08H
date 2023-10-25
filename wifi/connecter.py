import network
import ubinascii
from machine import Pin
from time import sleep


class WifiConnecter:
    def __init__(self, login: str, password: str) -> None:
        self.login = login
        self.__password = password
        self.__wlan = network.WLAN(network.STA_IF)
    
    
    def check_connection(self) -> bool:
        counter = 0
        print('\nconnection to:', self.login)
        while not self.__wlan.isconnected() and counter < 60:
            print('.', end='')
            counter += 1
            sleep(0.5)
        print()
        
        return self.__wlan.isconnected()
        
        
    def connect(self) -> bool:
        self.__wlan.active(True)
        
        if not self.__wlan.isconnected():
            self.__wlan.connect(self.login, self.__password)
            return self.check_connection()
        else:
            print('(Connection already exists)\n')
            return True
        
        
    def get_info(self) -> dict:
        info = {
            'AP:': self.login,
            'MAC:': ubinascii.hexlify(network.WLAN().config('mac'),':').decode(),
            'IP:': self.__wlan.ifconfig()[0],
            'MASK:': self.__wlan.ifconfig()[1],
            'GATEWAY': self.__wlan.ifconfig()[2]
        }
        
        return info
