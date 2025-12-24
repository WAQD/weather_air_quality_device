

from typing import Callable


class MotionSensor:
    def __init__(self, pin):
        self.pin = pin
        self.when_activated: Callable|None = None

    def close(self):
        pass