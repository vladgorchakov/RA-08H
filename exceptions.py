class BaudrateException(Exception):
    def __init__(self, baudrate):
        self.baudrate = baudrate

    def __str__(self):
        return f"{self.baudrate} is invalid. Baudrate should not be more than 9600"


class OTAAJoinModeException(Exception):
    def __str__(self):
        return f'The method should only be used for OTAA join mod.'


class ABPJoinModeException(Exception):
    def __str__(self):
        return f'The method should only be used for ABP join mod.'


class SizeDevAddrException(Exception):
    def __init__(self, size):
        self.correct_size = 8
        self.incorrect_size = size

    def __str__(self):
        return f'DevAddr size should be {self.correct_size} not {self.incorrect_size}'
