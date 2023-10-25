class LPPcodec:
    def __init__(self):
        self.__measure_type = {
            'temperature': '67'
            }
    
    def encode_to_hex(self, value): # сделать обработка на случай дробных значений
        value = hex(int(value * 10))[2:]
        if len(value) != 4:
            value = '0' * (4 - (len(value) % 4)) + value
        print("encode value -> " + value)
        return value
    
    def encode_to_hex_humidity(self, value):
        value = hex(int(value * 2))[2:]
        if len(value) < 2:
            value = '0' + value
        print("encode value -> " + value)
        return value
    
    def __encode_channel(self, channel):
        channel = str(channel)
        if len(channel) % 2:
            channel = '0' + channel
        return channel
        
    def encode_temp(self, value, channel=1):
        channel = self.__encode_channel(channel)
        return channel + '67'  + self.encode_to_hex(value)
    
    def encode_humidity(self, value, channel=1):
        channel = self.__encode_channel(channel)
        return channel + '68'  + self.encode_to_hex_humidity(value)
    
    def encode_humtemp(self, values, channel=1):
        return self.encode_humidity(values[0]) + self.encode_temp(values[1])
