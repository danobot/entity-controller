import appdaemon.plugins.hass.hassapi as hass

class MotionLight(hass.Hass):
    def initialize(self):
        self.timer = None

    def motion(self, delay):
        """
            Sensor callback: Called when the supplied sensor/s change state.
        """
        self.timer = self.run_in(self.light_off, delay)

    
    def light_off(self, kwargs):
        self.turn_off('light.test_light')
