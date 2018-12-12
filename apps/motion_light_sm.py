import appdaemon.plugins.hass.hassapi as hass
import paho.mqtt.client as mqtt
from transitions import Machine
PACKAGES = ['paho.mqtt.client']


# Version:          v0.4.0
# Documentation:    https://github.com/danobot/appdaemon-motion-lights

VERSION = '0.4.0'

LOG_BREAK = "-----------------------------------------------------------------------------------------";
class MotionLight(hass.Hass):
    
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
    overrideSwitch = None;
    stateEntities = None;
    entities = None;
    # Default states
    OFF_STATE = "off"
    ON_STATE = "on"
    SENSOR_ON_STATE = "on"


    def initialize(self):

        self.timer = None

        if "entity" in self.args: # definition of entity tells program to use this entity when checking state (ie. don't use state of entity_on bceause it might be a script.)
            self.theEntity = self.args["entity"]
        elif "entities" in self.args: 
            self.entities = self.args['entities']
        else:
            self.theEntity = self.args["entity_on"]

        if "state_entities" in self.args: # will control all enti OR the states of all entities and use the result.
            self.stateEntities = self.args['state_entities']

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

        if "override_switch" in self.args:
            self.overrideSwitch = self.args["override_switch"]

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


    def find_state(self):
        """
            Returns the state of the defined entities.
        """

        state = None;

        if self.stateEntities is not None or self.entities is not None:
            
            myEntities = None;
            if self.stateEntities is not None:
                myEntities = self.stateEntities;
                self.log("Using STATE entities for state observation.")
            else: 
                myEntities = self.entities;
                self.log("Using CONTROL entities for state observation.")

            for e in myEntities:
                s = self.get_state(e);
                state = state or s == self.ON_STATE;
                self.log(" * State of {} is {} and cumulative state is {}".format(e, s, state));
            return self.ON_STATE if state else self.OFF_STATE;

        if self.theEntity is not None:
            state = self.get_state(self.theEntity)
            self.log("Current state of {} is {}".format(self.theEntity, state), level="INFO")
        elif self.entityOn is not None:
            state = self.get_state(self.entityOn)
            self.log("Current state of {} is {}".format(self.entityOn, state), level="INFO")

        else:
            self.log("No entity defined whose state can be observed.");       


        return state;

    def motion(self, entity, attribute, old, new, kwargs):
        """
            Sensor callback: Called when the supplied sensor/s change state.
        """

        if new == self.SENSOR_ON_STATE:
            self.log(LOG_BREAK);

            if self.overrideSwitch:
                overrideSwitchState = self.get_state(self.overrideSwitch);
                if overrideSwitchState == "off":
                    self.log("MotionLight disabled by override switch " + self.overrideSwitch);
                    self.log(LOG_BREAK);
                    return;
                

            self.log("Sensor {} triggered".format(entity));
            # Use activeEntity state if it exists
            entityState = self.find_state(); # "entity" is guaranteed to be the active entity


            if entityState == self.OFF_STATE:
                if self.entityOn:
                    self.turn_on_entity(self.entityOn)
                elif self.theEntity: 
                    self.turn_on_entity(self.theEntity)
                elif self.entities is not None:
                    self.log("Turning on multiple entities:")
                    for e in self.entities:
                        self.turn_on_entity(e)

                else:
                    self.log("No entities supplied.");

                self.start_timer()

            else:
                if self.isOn:
                    self.log("New motion detected. Resetting timer.")
                    self.start_timer()
                else:
                    self.log("Entity is already switched on. Motion trigger ignored.")
                    self.log(LOG_BREAK);

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
                elif self.entityOn is not None: # if not, then turn off entity_on
                    self.log("Off: Turning {} off".format(self.entityOn))
                    self.turn_off(self.theEntity)
                elif self.entities is not None: # turn off entitites
                    for e in self.entities:
                        self.turn_off(e);
                        self.log("Turning off {}".format(e));
                else:
                    self.turn_off(self.theEntity)
                    self.log("No entities supplied that could be turned off.")
                
                self.isOn = False
        else:
            self.log("A timer expired but the light was not switched on by appdaemon. This should not happen, ever.")
        self.log(LOG_BREAK);

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
        if self.timer:
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
