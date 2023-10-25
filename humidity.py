import dht
import machine
import time
import ujson


class HumSensor:
    def __init__(self, pin: int, name='humidity', place='my room') -> None:
        self.name = name
        self.place = place
        self.pin = machine.Pin(pin)
        self.__hum = 0
        self.__temp = 0
        self.__sensor = dht.DHT11(self.pin)
        self.__log = []
        self.__timer = machine.Timer(1)
    
    
    @property
    def humidity(self) -> int:
        while True:
            try:
                print('checking')
                self.__sensor.measure()
                self.__hum = self.__sensor.humidity()            
                return self.__hum
            except:
                print('ERROR of updating value from .measure()')
                time.sleep(2)
                
                
    
    @property
    def temp(self) -> int:
        while True:
            try:
                self.__sensor.measure()
                self.__temp = self.__sensor.temperature()
                return self.__temp 
            except:
                print('ERROR of updating value from .measure()')
                time.sleep(2)
                
    
    @property
    def humtemp(self) -> tuple:
        while True:
            try:
                self.__sensor.measure()
                return self.__sensor.humidity(), self.__sensor.temperature()
            except:
                print('ERROR of updating value from .measure()')
                time.sleep(2)
                
                
    def add_to_log(self, timer):
        if len(self.__log) < 50:
                self.__log.append(self.humtemp)
        else:
            self.__log = self.__log[1:] + [self.humtemp]
        
    
    def scan(self, period=300000):
        self.__timer.init(period=period, mode=machine.Timer.PERIODIC, callback=self.add_to_log)
    
    
    def humtemp_json(self):
        while True:
            try:
                self.__sensor.measure()
                payload = {
                        'temp': self.__sensor.temperature(),
                        'humidity': self.__sensor.humidity()   
                        }
                return ujson.dumps(payload)
            
            except:
                print('ERROR of updating value from .measure()')
                time.sleep(2)
        
    @property
    def log(self):
        return self.__log
    

def main() -> None:
    hudm = HumSensor(18)
    print(f'*Sensor*\nName: {hudm.name}; Place: {hudm.place}')
    
    #1 using humidity and temp properties
    print(f'Temperature: {hudm.temp}')
    time.sleep(1)
    print(f'Hudmitity: {hudm.humidity}')
    time.sleep(1)
    
    #2 using humtemp propertyss
    hudm_temp = hudm.humtemp
    print(f'Temperature: {hudm_temp[0]}')
    print(f'Hudmitity: {hudm_temp[1]}')


if __name__=='__main__':
    main()
