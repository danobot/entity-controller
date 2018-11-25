import appdaemon.plugins.hass.hassapi as hass
import paho.mqtt.client as mqtt

PACKAGES = ['paho.mqtt.client']

# App to turn lights on when motion detected then off again after a delay
#
# Use with constrints to activate only for the hours of darkness
#
# Args:
#
# sensor: binary sensor to use as trigger
# entity_on : entity to turn on when detecting motion, can be a script, scene or anything else that can be turned on. Must specify entity containing state
# entity: entity used to observe state. This is required because sometimes `entity_on` does not have state (e.g. scene, script). Can be used as a replacement for entity_on
# entity_off : entity to activate after time out. If you want to activate a script, scene. If blank, entity_on will be switched off. Hence not required if entity_on can be switched on and switched off.
# delay: amount of time after turning on to turn off again. If not specified defaults to 3 minutes.
# night_start_time: After this time (e.g. 11pm, motionlight will use delay_night timeout period)
# night_end_time
# delay_night: delay in seconds used after going to bed
# brightness: brightness percentage to use at nightime (only specify this for entities that support brightness.)
# topic: required to detect if entity is modified during the timeout period. **Should use entity state instead (last modified value)
# off_state: default "off", overwrite off state if required
# on_state: default "on", overwrite on state if required 
#
# Documentation: https://github.com/danobot/appdaemon-motion-lights


class MotionLights(hass.Hass):
    
    timer = None
    isOn = False
    # myName = 'Unnamed'
    delay = 180 # default delay = 3 minutes
    stay = False
    brightness = None
    topic = None
    theEntity = None
    entityOn = None
    entityOff = None
    delay_night = None
    lastDelay = None
    night_mode = None;

    # Default states
    OFF_STATE = "off"
    ON_STATE = "on"


    def initialize(self):

        self.timer = None

        if "entity" in self.args: # definition of entity tells program to use this entity when checking state (ie. don't use state of entity_on bceause it might be a script.)
            self.theEntity = self.args["entity"]
        else:
            self.theEntity = self.args["entity_on"]

        if "entity_on" in self.args:
            self.entityOn = self.args["entity_on"]

        if "entity_off" in self.args:
            self.entityOff = self.args["entity_off"]

        if "delay" in self.args:
            self.delay = self.args["delay"]

        if "stay" in self.args:
            self.stay = self.args["stay"]

        if "brightness" in self.args:
            self.brightness = self.args["brightness"]

        if "night_mode" in self.args:
            self.night_mode = self.args["night_mode"]
            if not "start_time" in self.night_mode:
                self.log("Night mode requires a start_time parameter !")

            # if not "brightness" in self.night_mode:
            #     self.night_mode['brightness'] = None
            
            if not "end_time" in self.night_mode:
                self.log("Night mode requires a end_time parameter !")
            
        if "on_state" in self.args:
            self.ON_STATE = self.args["on_state"]

        if "off_state" in self.args:
            self.OFF_STATE = self.args["off_state"]

        # Monitor topic for commands sent to entity. Used to cancel timer if entity is controlled within timeout period.
        if "topic" in self.args:
            self.log("Topic: " + self.args["topic"])
            self.topic = self.args["topic"]
            # self.mqtt_subscribe(self, self.topic)
            # self.listen_event(self.on_message, "MQTT_MESSAGE", topic = self.topic)
            client = mqtt.Client()
            client.on_connect = self.on_connect
            client.on_message = self.on_message

            client.connect("mqtt", 1883, 60)


        # Check some Params

        # Subscribe to sensors - change this to passed in RF code and MQTT topic subscription.
        if "sensor" in self.args:
            self.listen_state(self.motion, self.args["sensor"])
        elif "sensors" in self.args:
            for sensor in self.args["sensors"]:
                self.log("Registering multiple sensors: " + sensor)
                self.listen_state(self.motion, sensor)
        else:
            self.log("No sensor specified, doing nothing")

    def motion(self, entity, attribute, old, new, kwargs):
        """
            Sensor callback: Called when the supplied sensor/s change state.
        """
        if new == self.ON_STATE:
            self.log("Motion Sensor {} triggered".format(entity))
            # Use activeEntity state if it exists
            entityState = self.get_state(self.theEntity) # "entity" is guaranteed to be the active entity

            self.log("Current state of {} is {}".format(self.theEntity, entityState), level="INFO")

            if entityState == self.OFF_STATE:
                if self.entityOn:
                    self.turn_on_entity(self.entityOn)
                else: 
                    self.turn_on_entity(self.theEntity)
                self.start_timer()

            else:
                if self.isOn:
                    self.log("New motion detected. Resetting timer.")
                    self.start_timer()
                else:
                    self.log("Entity is already switched on. Motion trigger ignored.")

    def light_off(self, kwargs):
        """
            Timeout callback: called when the timer expires
        """
        self.log("Timer elapsed.")
        if self.isOn: # Light was switched on by MotionLight.

            if self.stay:
                self.log("Light stays on after motion detection.")
            else:
                if self.entityOff is not None: # check if an "off" script is supplied
                    self.turn_on(self.entityOff)
                    self.log("Off: Activating {} ".format(self.entityOff))
                else: # if not, then turn off entity_on
                    self.log("Off: Turning {} off".format(self.entityOn))
                    self.turn_off(self.theEntity)
                self.isOn = False
        else:
            self.log("A timer expired but the light was not switched on by appdaemon. This should not happen, ever.")
   
    def turn_on_entity(self, entity):
        self.log("Turning {} on".format(entity))
        if self.is_night_mode() and 'brightness' in self.night_mode:
            self.log("Night time brightness ({}%) overwrites default ({}%)".format(self.night_mode['brightness'], self.brightness), level="INFO")
            self.turn_on(entity, brightness = self.night_mode['brightness'])
        elif self.brightness:
            self.log("Using default brightness ({})".format(self.brightness), level="INFO")
            self.turn_on(entity, brightness = self.brightness)
        else:
            self.log("No brightness specified", level="INFO")
            self.turn_on(entity)
        self.isOn = True # means that the light was turned on by AppDaemon (used in light_off)
        
    def start_timer(self):
        self.cancel_timer(self.timer) # cancel previous timer
        if self.is_night_mode() and 'delay' in self.night_mode:
            self.log("Starting timer for {} seconds: night time delay ({} sec) overwrites default ({} sec)".format(self.night_mode['delay'],self.night_mode['delay'], self.delay), level="INFO")
            self.timer = self.run_in(self.light_off, self.night_mode['delay'])
        else:
            self.log("Starting timer for {} seconds".format(self.delay), level="INFO")
            self.timer = self.run_in(self.light_off, self.delay)
                        


    def is_night_mode(self):
        return self.night_mode and self.now_is_between(self.night_mode['start_time'], self.night_mode['end_time']);


    def on_connect(client, userdata, flags, rc):
        self.log("Connected with result code ")

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe(self.topic)

    def on_message(client, userdata, msg):
        self.log("Entity was controlled within timeout period. Cancelling timer.")
        self.cancel_timer(self.timer)
        self.log(msg.topic+" "+str(msg.payload))
