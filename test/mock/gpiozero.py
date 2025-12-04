

class MotionSensor:
    def __init__(self, pin):
        self.pin = pin
        self.when_activated = None

    def close(self):
        pass