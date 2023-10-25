from machine import UART, SoftI2C, Pin
from time import sleep
from humidity import HumSensor
from cayenne import LPPcodec
from ra08h import RA08H
from display import ssd1306
from logger import to_file
from microgps import MicropyGPS

def pin_state(pin):
    values = []
    n = 5
    for i in range(5):
        values.append(pin.value())
        sleep(0.1)
    if sum(values) == n:
        return True
    else:
        return False

    

def send_log_to_uart(data):
    if data[0]:
        print('tx data -> ok')
    else:
        print('tx data -> no')

    print('\n\n***LOGS***')
    for key, value in data[1].items():
        print('\n_________________________')
        print(key + ':')
        for key1, val1 in value.items():
            print(key1 + ' -> ' + str(val1))
            

def send_log_to_lcd(oled, data, cnt):
    oled.fill(0)
    oled.text("CNT: " + str(cnt), 0, 0)
    if data[0]:
        oled.text("STATUS: OK", 0, 20)
        oled.text("DATERATE: " + data[1]["received_data"]["daterate"], 0, 30)
        oled.text("RSSI: " + data[1]["received_data"]["rssi"], 0, 40)
        oled.text("SNR: " + data[1]["received_data"]["snr"], 0, 50)
    else:
        oled.text("STATUS: FAIL", 0, 20)
    oled.show()


def main():
    daterate = 5
    pin = Pin(22, Pin.IN, Pin.PULL_DOWN)
    pin1 = Pin(14, Pin.OUT)
    uart = UART(2, 9600, tx=17, rx=16)
    lora = RA08H(uart)
    lora.set_date_rate(daterate)
    hs = HumSensor(18)
    codec = LPPcodec()
    i2c = SoftI2C(scl=Pin(26), sda=Pin(25))
    oled_width = 128
    oled_height = 64
    oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

    
    cnt = 0
    oled.fill(0)
    oled.text('Join...', 0, 0)
    oled.show()
    
    while True:
        status, join_msg = lora.join()
        cnt += 1
        print(cnt)
        oled.fill(0)
        oled.text('Join...', 0, 0)
        oled.text("ST: " + join_msg["STATUS"], 0, 10)
        oled.text("MSG: " + join_msg["MSG"], 0, 20)
        oled.text("CNT: " + str(cnt), 0, 30)
        oled.show()
        
        if status:
            break
    
    
    cnt = 0
    while lora.is_join:
        if pin_state(pin):
            if daterate > 0:
                daterate -= 1
                pin1.on()
                lora.set_date_rate(daterate)
                print("set daterate: ", daterate)
                pin1.off()
            else:
                daterate = 5

        humtemp = hs.humtemp
        temp_lpp = codec.encode_humtemp(humtemp)
        print("humidity: ->", humtemp[0])
        print("temperature: ->", humtemp[1])
        print("encode data: ->", temp_lpp)
        data = lora.send_data(temp_lpp)
        cnt += 1
        send_log_to_lcd(oled, data, cnt)
        send_log_to_uart(data)

                  
if __name__ == '__main__':
    main()
