"""
State Machine-based Motion Lighting Implementation (Home Assistant Component)
Maintainer:       Daniel Mason
Version:          v1.2.0 - Component Rewrite
Documentation:    https://github.com/danobot/appdaemon-motion-lights

"""
import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import entity
from homeassistant.components.light import ATTR_BRIGHTNESS, Light, PLATFORM_SCHEMA

_LOGGER = logging.getLogger(__name__)
DOMAIN = 'lightingsm'
# DEPENDENCIES = ['transitions','threading','time']
REQUIREMENTS = ['transitions==0.6.9'] # ,'logging==0.4.9.6'
DEFAULT_NAME = 'Motion Light'
CONF_NAME = 'name'
CONF_CONTROL = 'entities'
CONF_SENSORS = 'sensors'
CONF_STATE = 'state_entities'
CONF_DELAY= 'delay'
CONF_NIGHT_MODE = 'night_mode'

# PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
#     vol.Required(CONF_NAME, default=DEFAULT_NAME): cv.string,
#     vol.Required(CONF_CONTROL): cv.entity_ids,
#     vol.Required(CONF_SENSORS): cv.entity_ids,
#     vol.Optional(CONF_STATE): cv.entity_ids,
#     vol.Optional(CONF_DELAY): cv.positive_int
# })

devices = []

def setup_platform(hass, config, add_devices, discovery_info=None):
    # from lsm import LightingSM
    myconfig = config
    _LOGGER.info("The {} component is ready! {}".format(DOMAIN, myconfig))

    # Get the text from the configuration. Use DEFAULT_TEXT if no name is provided.
    # text = config[DOMAIN].get(CONF_TEXT, DEFAULT_TEXT)

    _LOGGER.info("Config: "  + str(myconfig))

    for key, config in myconfig.get('entities').items():
        _LOGGER.info("Config Item {}: {}".format(str(key), str(config)))
        config["name"] = key
        devices.append(LightingSM(hass, config))


    add_devices(devices)
    return True


# import appdaemon.plugins.hass.hassapi as hass

VERSION = '1.2.0'
SENSOR_TYPE_DURATION = 1
SENSOR_TYPE_EVENT = 2
DEFAULT_DELAY = 180
DEFAULT_BRIGHTNESS = 100
DOMAIN = 'lightingsm'
class LightingSM(entity.Entity): # https://dev-docs.home-assistant.io/en/master/api/helpers.html#module-homeassistant.helpers.entity

    
    
    
    STATES = ['idle', 'disabled', {'name': 'active', 'children': ['timer','stay_on'], 'initial': False}]
    stateEntities = None
    controlEntities = None
    sensorEntities = None
    offEntities = None
    timer_handle = None
    sensor_type = None
    night_mode = None
    backoff = False
    backoff_count = 0
    light_params_day = {}
    light_params_night = {}
    name = None

    def __init__(self, hass, config):
        import logging
        from transitions import Machine
        from transitions.extensions import HierarchicalMachine as Machine
        from threading import Timer
        from datetime import datetime  
        from datetime import timedelta  
        logger = logging.getLogger(__name__ + '.' + config.get('name'))
        logger.debug("Init LightingSM with: " + str(config))
        self.name = config.get('name')
        logger.debug("Name: " + str(self.name))
        
        self.machine = Machine(model=self, 
            states=self.STATES, 
            initial='idle', 
            # title=self.name+" State Diagram",
            # show_conditions=True
            # show_auto_transitions = True,
            # finalize_event=self.draw
        )

        self.machine.add_transition(trigger='disable',              source='*',                 dest='disabled')

        # Idle
        self.machine.add_transition(trigger='sensor_off',           source='idle',              dest=None)
        self.machine.add_transition(trigger='sensor_on',            source='idle',              dest='active',          conditions=['is_state_entities_off'])
        # Disabled      
        self.machine.add_transition(trigger='enable',               source='disabled',          dest='idle')
        self.machine.add_transition(trigger='sensor_on',            source='disabled',          dest=None)
        

        self.machine.add_transition(trigger='sensor_off',           source='disabled',          dest=None)

        self.machine.add_transition(trigger='enter',                source='active',            dest='active_timer',    unless='will_stay_on')
        self.machine.add_transition(trigger='enter',                source='active',            dest='active_stay_on',  conditions='will_stay_on')

        # Active Timer
        self.machine.add_transition(trigger='sensor_on',            source='active_timer',      dest=None,              after='_reset_timer')
        self.machine.add_transition(trigger='sensor_off',           source='active_timer',      dest=None,              conditions=['is_event_sensor'])
        self.machine.add_transition(trigger='sensor_off_duration',  source='active_timer',      dest='idle',            conditions=['is_timer_expired'])
        self.machine.add_transition(trigger='timer_expires',        source='active_timer',      dest='idle',            conditions=['is_event_sensor'])
        self.machine.add_transition(trigger='timer_expires',        source='active_timer',      dest='idle',            conditions=['is_duration_sensor', 'is_sensor_off'])

        # self.machine.add_transition(trigger='sensor_off', source='active', dest='idle')
        self.machine.add_transition(trigger='sensor_off',           source='active_stay_on',    dest=None)
        self.machine.add_transition(trigger='timer_expires',        source='active_stay_on',    dest=None)
        
        # Active Timer Normal
		
        # self.machine.add_transition(trigger='timer_expires', source='active_timer_normal', dest='idle', conditions=['is_event_sensor'])
        # self.machine.add_transition(trigger='control',    source='active', dest='idle', before='_cancel_timer')

        # duration sensor: we want to turn off if:
            # * timer expires. sensor is off
            # * sensor turns off and timer has expired
        # do not turn off if
            # * sensor is on and timer expires
        self.config_static_strings(config)
        self.config_state_entities(config)
        self.config_control_entities(config) # must come after config_state_entities
        self.config_sensor_entities(config)
        self.config_off_entities(config)
        self.config_normal_mode(config) 
        self.config_night_mode(config) #must come after normal_mode
        self.config_other(config)

    def draw(self):
        self.update()
        if self.do_draw:
            self.log("Updating graph in state: " + self.state)
            self.get_graph().draw(self.image_path + self.image_prefix + str(self.name)+'.png', prog='dot', format='png')


    def update(self, **kwargs):
        self.set_state("{}.{}".format(DOMAIN,str(self.name)), state=self.state, attributes=kwargs)

    def clear_state_attributes(self):
        kwargs = {}
        kwargs["reset_count"] = None
        kwargs["reset_at"] = None
        kwargs["expires_at"] = None
        kwargs["delay"] = None
        kwargs["disabled_by"] = None
        kwargs["disabled_at"] = None
        kwargs["service_data"] = None
        # kwargs["last_triggered_by"] = None
        # kwargs["last_triggered_at"] = None

        self.set_state("{}.{}".format(DOMAIN,str(self.name)), state=self.state, attributes=kwargs)
    # =====================================================
    # S T A T E   C H A N G E   C A L L B A C K S
    # =====================================================

    def sensor_state_change(self, entity, attribute, old, new, kwargs):
        self.log("Sensor state change")
        if self.matches(new, self.SENSOR_ON_STATE):
            self.update(last_triggered_by=entity)
            self.sensor_on()
        if self.matches(new,self.SENSOR_OFF_STATE) and self.sensor_type == SENSOR_TYPE_DURATION:
            self.update(last_triggered_by=entity)
            # We only care about sensor off state changes when the sensor is a duration sensor.
            self.sensor_off_duration()

    def override_state_change(self, entity, attribute, old, new, kwargs):
        if self.matches(new, self.OVERRIDE_ON_STATE):
            self.update(disabled_by=entity)
            self.disable()
            self.update(disabled_at=str(datetime.now()))
        if self.matches(new, self.OVERRIDE_OFF_STATE) and not self._override_entity_state():
            self.enable()


    def control_state_change(self, entity, attribute, old, new, kwargs):
        self.log(self.is_active_timer_normal())
        if self.is_active_timer_normal():
            self.control()

    def event_handler(self,event, data, el,**kwargs):
        self.log("Event: " + str(event))
        self.log("Data: " + str(data))
        self.log("kwargs: " + str(el))

        if data['entity_id'] == self.name:
            self.log("It is me!")
            if event == 'lightingsm-reset':
                self.machine.set_state('idle')
                self.log("Reset was called")


    def _start_timer(self):
        self.logger.info(self.lightParams)
        if self.backoff_count == 0:
            self.previous_delay = self.lightParams.get('delay', DEFAULT_DELAY)
        else:
            self.log("Backoff: {},  count: {}, delay{}, factor: {}".format(self.backoff,self.backoff_count, self.lightParams.get('delay',DEFAULT_DELAY), self.backoff_factor))
            self.previous_delay = round(self.previous_delay*self.backoff_factor, 2)
            if self.previous_delay > self.backoff_max:
                self.log("Max backoff reached. Will not increase further.")
                self.previous_delay = self.backoff_max

        self.timer_handle = Timer(self.previous_delay, self.timer_expire)
        self.log("Delay: " + str(self.previous_delay))
        self.timer_handle.start()
        expiry_time = str(datetime.now() + timedelta(seconds=self.previous_delay));
        self.update(delay=self.previous_delay, expires_at=expiry_time)
    
    def _cancel_timer(self):
        if self.timer_handle.is_alive():
            self.timer_handle.cancel()

    def _reset_timer(self):
        self.log("Resetting timer" + str(self.backoff))
        self._cancel_timer()
        if self.backoff:
            self.log("inc backoff")
            self.backoff_count += 1
            self.update(reset_count=self.backoff_count,reset_at=str(datetime.now()))
        self._start_timer()
        # self.log(str(self.timer_handle))
        return True

       

    # =====================================================
    # S T A T E   M A C H I N E   C O N D I T I O N S
    # =====================================================
    def _override_entity_state(self):
        for e in self.overrideEntities:
            s = self.get_state(e)
            self.logger.info(s)
            self.logger.info(" * State of {} is {}".format(e, s))
            if self.matches(s, self.OVERRIDE_ON_STATE):
                self.logger.debug("Override entities are ON. [{}]".format(e))
                return True
        self.logger.debug("Override entities are OFF.")
        return False

    def _sensor_entity_state(self):
        for e in self.sensorEntities:
            s = self.get_state(e)
            self.logger.info(s)
            self.logger.info(" * State of {} is {}".format(e, s))
            if self.matches(s, self.SENSOR_ON_STATE):
                self.logger.debug("Sensor entities are ON. [{}]".format(e))
                return True
        self.logger.debug("Sensor entities are OFF.")
        return False

    def is_sensor_off(self):
        return self._sensor_entity_state() == False

    def is_sensor_on(self):
        return self._sensor_entity_state()
        
    def _state_entity_state(self):
        for e in self.stateEntities:
            s = self.get_state(e)
            self.logger.info(s)
            self.log(" * State of {} is {}".format(e, s))
            if self.matches(s, self.STATE_ON_STATE):
                self.logger.debug("State entities are ON. [{}]".format(e))
                return True
        self.logger.debug("State entities are OFF.")
        return False
    
    def is_state_entities_off(self):
        return self._state_entity_state() == False

    def is_state_entities_on(self):
        return self._state_entity_state()
    
    def will_stay_on(self):
        return _config.get('stay', False)

    def is_night(self):
        if self.night_mode is None:
            self.logger.debug("(night mode disabled): " + str(self.night_mode))
            self.update(night_mode='on')
            return False
        else:
            self.update(night_mode='off')
            self.logger.debug("NIGHT MODE ENABLED: " + str(self.night_mode))
            # start=  self.parse_time(self.night_mode['start_time'])
            # end=  self.parse_time(self.night_mode['end_time'])
            # http://dev-docs.home-assistant.io/en/master/api/util.html#homeassistant.util.dt.parse_time
            return self.now_is_between(self.night_mode['start_time'], self.night_mode['end_time'])



    def is_event_sensor(self):
        return self.sensor_type == SENSOR_TYPE_EVENT

    def is_duration_sensor(self):
        return self.sensor_type == SENSOR_TYPE_DURATION

    def is_timer_expired(self):

        expired = self.timer_handle.is_alive() == False
        self.logger.debug("is_timer_expired -> " + str(expired))
        return expired
    
    def timer_expire(self):
        # self.log("Timer expired")
        if self.is_duration_sensor():
            self.logger.debug("It's a DURATION sensor")
            if self.is_sensor_off():
                self.logger.debug("Sensor entities are OFF.")
                self.timer_expires()
        else:    
            self.timer_expires()


    # =====================================================
    # S T A T E   M A C H I N E   C A L L B A C K S
    # =====================================================
    def on_enter_idle(self):
        self.log("Entering idle")
        self.clear_state_attributes()
        # self.draw();

    def on_exit_idle(self):
        self.log("Exiting idle")

    def on_enter_disable(self):
        self.log("Now disabled")


    def on_enter_active(self):
        self.update(last_triggered_at=str(datetime.now()))
        self.backoff_count = 0
        if self.is_night():
            self.logger.debug("Using NIGHT MODE parameters: " + str(self.light_params_night))
            self.lightParams = self.light_params_night
        else:
            self.logger.debug("Using DAY MODE parameters: " + str(self.light_params_day))
            self.lightParams = self.light_params_day

        self.update(service_data=self.lightParams['service_data'])
        self._start_timer()

        self.logger.debug("light params before turning on: " + str(self.lightParams))
        for e in self.controlEntities:
            # self.logger.debug("brightness value" + str(self.lightParams.get('brightness')))
            if self.lightParams.get('service_data') is not None:
                self.logger.debug("Turning on {} with service parameters {}".format(e, self.lightParams.get('service_data')))
                self.log("Turning on {} with service parameters {}".format(e, self.lightParams.get('service_data')))
                self.turn_on(e, **self.lightParams.get('service_data'))
            else:
                self.logger.debug("Turning on {} (no parameters passed to service call)".format(e))
                self.turn_on(e)
        self.enter()

    def on_exit_active(self):
        self.log("Turning off entities, cancelling timer")
        self._cancel_timer() # cancel previous timer


        if self.offEntities is not None:
            self.logger.info("using oFF entitesi")
            for e in self.offEntities:
                self.logger.info("Turning on {}".format(e))
                
                self.log("Turning on {}".format(e))
                self.turn_on(e)
        else:
            for e in self.controlEntities:
                self.log("Turning off {}".format(e))
                self.turn_off(e)

    
    # =====================================================
    #    C O N F I G U R A T I O N  &  V A L I D A T I O N
    # =====================================================



    def config_control_entities(self, _config):
    
        self.log("Setting up control entities")
        self.controlEntities = []

        if "entity" in _config: # definition of entity tells program to use this entity when checking state (ie. don't use state of entity_on bceause it might be a script.)
            self.controlEntities.append( _config["entity"])

        if "entities" in _config: 
            self.controlEntities.extend( _config['entities'])

        if "entity_on" in _config: 
            self.controlEntities.append( _config["entity_on"] )


        #for control in self.controlEntities:
        #   self.log("Registering control: " + str(control))
        #   self.listen_state(self.control_state_change, control)


        # IF no state entities are defined, use control entites as state
        if self.stateEntities is None:
            self.stateEntities = []
            self.stateEntities.extend(self.controlEntities)
            self.log("Added Control Entities as state entities: " + str(self.stateEntities))
            self.update(state_entities=self.stateEntities)
        self.update(control_entities=self.controlEntities)
        self.log("Control Entities: " + str(self.controlEntities))

    def config_state_entities(self, _config):
        
        self.log("Setting up state entities")
        if _config.get('state_entities',False): # will control all enti OR the states of all entities and use the result.
            self.log("config defined")
            self.stateEntities = []
            self.stateEntities.extend(_config.get('state_entities',[]))
            self.update(state_entities=self.stateEntities)
        self.log("State Entities: " + str(self.stateEntities))

    def config_off_entities(self, _config):
    
        temp = _config.get("entity_off", None)
        if temp is not None:
            self.log("Setting up off entities")
            self.offEntities = []
            if type(temp) == str:
                self.offEntities.append(temp)
            else:
                self.offEntities.extend(temp)
            self.update(off_entities=self.offEntities)
            self.logger.info('entities: ' + str(self.offEntities))


    def config_sensor_entities(self, _config):
        self.sensorEntities = []
        temp = _config.get("sensor", None)
        if temp is not None:
            self.sensorEntities.append(temp)
            
        temp = _config.get("sensors", None)
        if temp is not None:
            self.sensorEntities.extend(temp)


        # self.sensorEntities = [];
        # temp = _config.get("sensor", [])
        # self.sensorEntities.extend(temp)
            
        # temp = _config.get("sensors", [])
        # self.sensorEntities.extend(temp)


            
        
        if self.sensorEntities.count == 0:
            self.log("No sensor specified, doing nothing")

        self.log("Sensor Entities: " + str(self.sensorEntities))
        self.update(sensor_entities=self.sensorEntities)

        for sensor in self.sensorEntities:
            self.log("Registering sensor: " + str(sensor))
            self.listen_state(self.sensor_state_change, sensor)

    

    def config_static_strings(self, _config):
        DEFAULT_ON = ["on","playing","home"]
        DEFAULT_OFF = ["off","idle","paused","away"]
        self.CONTROL_ON_STATE = _config.get("control_states_on", DEFAULT_ON)
        self.CONTROL_OFF_STATE = _config.get("control_states_off", DEFAULT_OFF)
        self.SENSOR_ON_STATE = _config.get("sensor_states_on", DEFAULT_ON)
        self.SENSOR_OFF_STATE = _config.get("sensor_states_off", DEFAULT_OFF)
        self.OVERRIDE_ON_STATE = _config.get("override_states_on", DEFAULT_ON)
        self.OVERRIDE_OFF_STATE = _config.get("override_states_off", DEFAULT_OFF)
        self.STATE_ON_STATE = _config.get("state_states_on", DEFAULT_ON)
        self.STATE_OFF_STATE = _config.get("state_states_off", DEFAULT_OFF)

        on = _config.get('state_strings_on', False)
        if on:
            self.CONTROL_ON_STATE.extend(on)
            self.CONTROL_ON_STATE.extend(on)
            self.SENSOR_ON_STATE.extend(on)
            self.OVERRIDE_ON_STATE.extend(on)
            self.STATE_ON_STATE.extend(on)

        off = _config.get('state_strings_off', False)
        if off:
            self.CONTROL_OFF_STATE.extend(off)
            self.SENSOR_OFF_STATE.extend(off)
            self.OVERRIDE_OFF_STATE.extend(off)
            self.STATE_OFF_STATE.extend(off)

    

    def matches(self, value, list):
        """
            Checks whether a string is contained in a list (used for matching state strings)
        """
        try:
            index = list.index(value)
            return True
        except ValueError:
            return False

    def config_night_mode(self, _config):
        """
            Configured night mode parameters. If no night_mode service parameters are given, the day mode parameters are used instead. If those do not exist, the 
        """
        if "night_mode" in _config:
            self.night_mode = _config["night_mode"]
            night_mode = _config["night_mode"]
            self.logger.info(night_mode)
            self.light_params_night['delay'] = night_mode.get('delay',_config.get("delay", DEFAULT_DELAY))
            self.light_params_night['service_data'] = night_mode.get('service_data',self.light_params_day.get('service_data'))
            self.logger.info(self.light_params_night)
            if not "start_time" in night_mode:
                self.log("Night mode requires a start_time parameter !")

            if not "end_time" in night_mode:
                self.log("Night mode requires a end_time parameter !")
            
    def config_normal_mode(self, _config):
        params = {}
        params['delay'] = _config.get("delay", DEFAULT_DELAY)
        params['service_data'] = _config.get("service_data", None)
        self.logger.info("serivce data set up: " + str(_config))
        self.light_params_day = params
    def config_other(self, _config):

        self.do_draw = _config.get("draw", False)
        
        if "entity_off" in _config:
            self.entityOff = _config.get("entity_off", None)
       
        self.image_prefix = _config.get('image_prefix','/fsm_diagram_')
        self.image_path = _config.get('image_path','/conf/temp')
        self.backoff = _config.get('backoff', False)

        if self.backoff:
            self.log("setting up backoff. Using delay as initial backoff value.")
            self.backoff_factor = _config.get('backoff_factor', 1.1)
            self.backoff_max = _config.get('backoff_max', 300)

        self.stay = _config.get("stay", False)
   
        self.overrideEntities = _config.get("overrides", None)

        if self.overrideEntities is not None:
            for e in self.overrideEntities:
                self.logger.info("Setting override callback/s: " + str(e))
                self.listen_state(self.override_state_change, e)
            self.update(override_entities=self.overrideEntities)
        if _config.get("sensor_type_duration"):
            self.sensor_type = SENSOR_TYPE_DURATION
        else:
            self.sensor_type = SENSOR_TYPE_EVENT


# class Strategy(LightingSM):
#     def __init__(self, delay, brightness):
#         self.delay = delay
#         self.brightness = brightness

#     def start(self):
#         raise NotImplementedError


