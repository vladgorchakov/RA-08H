"""Non-blocking debounced button driver for MicroPython.

Supports:
- Software debounce filtering via time.ticks_diff()
- Short press (click) and long press detection
- Event callbacks safely dispatched via micropython.schedule
- Non-blocking polling API (was_clicked(), was_long_pressed())
"""

import time

try:
    import micropython

except ImportError:
    class _MockMicroPython:
        @staticmethod
        def schedule(fn, arg):
            fn(arg)

        @staticmethod
        def alloc_emergency_exception_buf(size):
            pass

    micropython = _MockMicroPython()

try:
    from machine import Pin
except ImportError:
    Pin = None

if not hasattr(time, 'ticks_ms'):
    time.ticks_ms = lambda: int(time.time() * 1000)
    time.ticks_diff = lambda a, b: a - b
    time.sleep_ms = lambda ms: time.sleep(ms / 1000.0)

try:
    micropython.alloc_emergency_exception_buf(100)
except Exception:
    pass



class Button:
    """Non-blocking debounced button handler with click and long-press support."""

    EVENT_CLICK = 1
    EVENT_LONG_PRESS = 2

    def __init__(
        self,
        pin_num: int,
        on_click=None,
        on_long_press=None,
        debounce_ms: int = 50,
        long_press_ms: int = 2000,
        pull_down: bool = True
    ):
        self.pin_num = pin_num
        self.on_click = on_click
        self.on_long_press = on_long_press
        self.debounce_ms = debounce_ms
        self.long_press_ms = long_press_ms
        self.active_level = 1 if pull_down else 0

        self._press_start_time = 0
        self._is_pressed = False
        self._clicked_flag = False
        self._long_pressed_flag = False

        if Pin is not None:
            pull = Pin.PULL_DOWN if pull_down else Pin.PULL_UP
            self.pin = Pin(pin_num, Pin.IN, pull)
            # Interrupt on both rising and falling edges to track press duration
            self.pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._irq_handler)
        else:
            self.pin = None

    def _irq_handler(self, pin):
        """Hardware interrupt handler for pin state transitions."""
        val = pin.value()
        now = time.ticks_ms()

        if val == self.active_level:
            # Button down
            if not self._is_pressed:
                self._is_pressed = True
                self._press_start_time = now
        else:
            # Button released
            if self._is_pressed:
                self._is_pressed = False
                duration = time.ticks_diff(now, self._press_start_time)

                if duration >= self.debounce_ms:
                    if duration >= self.long_press_ms:
                        self._long_pressed_flag = True
                        if self.on_long_press is not None:
                            self._schedule(self.on_long_press)
                    else:
                        self._clicked_flag = True
                        if self.on_click is not None:
                            self._schedule(self.on_click)

    def _schedule(self, callback):
        try:
            micropython.schedule(self._dispatch, callback)
        except RuntimeError:
            pass

    def _dispatch(self, callback):
        if callback is not None:
            callback()

    # --- Polling API ---

    def was_clicked(self) -> bool:
        """Returns True once if a short click occurred since last call."""
        if self._clicked_flag:
            self._clicked_flag = False
            return True
        return False

    def was_long_pressed(self) -> bool:
        """Returns True once if a long press occurred since last call."""
        if self._long_pressed_flag:
            self._long_pressed_flag = False
            return True
        return False

    def was_pressed(self) -> bool:
        """Backward-compatible alias for was_clicked()."""
        return self.was_clicked()

    @property
    def is_held(self) -> bool:
        """Returns True if the button is currently held down."""
        if self.pin is None:
            return False
        return self.pin.value() == self.active_level
