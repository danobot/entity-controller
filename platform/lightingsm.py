"""
State Machine-based Motion Lighting Implementation (Home Assistant Component)
Maintainer:       Daniel Mason
Version:          v2.0.0 - Component Rewrite
Documentation:    https://github.com/danobot/appdaemon-motion-lights

"""
import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import entity, service, event
from homeassistant.components.light import ATTR_BRIGHTNESS, Light, PLATFORM_SCHEMA
from custom_components.lightingsm import StateMachine
# from homeassistant.components.switch import SwitchDevice
_LOGGER = logging.getLogger(__name__)

import logging
from transitions import Machine
from transitions.extensions import HierarchicalMachine as Machine
from threading import Timer
from datetime import datetime  
from datetime import timedelta  

# DEPENDENCIES = ['transitions','threading','time']
REQUIREMENTS = ['transitions==0.6.9'] # ,'logging==0.4.9.6'

DOMAIN = 'lightingsm'


VERSION = '2.0.0'
SENSOR_TYPE_DURATION = 1
SENSOR_TYPE_EVENT = 2
DEFAULT_DELAY = 180
DEFAULT_BRIGHTNESS = 100
DEFAULT_NAME = 'Motion Light'
CONF_NAME = 'name'
CONF_CONTROL = 'entities'
CONF_SENSORS = 'sensors'
CONF_STATE = 'state_entities'
CONF_DELAY= 'delay'
CONF_NIGHT_MODE = 'night_mode'

STATES = ['idle', 'disabled', {'name': 'active', 'children': ['timer','stay_on'], 'initial': False}]
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
    logging.basicConfig(level=logging.DEBUG)
    # Set transitions' log level to INFO; DEBUG messages will be omitted
    logging.getLogger('transitions').setLevel(logging.DEBUG)
    _LOGGER.info("The {} component is ready! {}".format(DOMAIN, myconfig))

    # Get the text from the configuration. Use DEFAULT_TEXT if no name is provided.
    # text = config[DOMAIN].get(CONF_TEXT, DEFAULT_TEXT)

    _LOGGER.info("Config: "  + str(myconfig))
    
    machine = Machine(states=STATES, 
        initial='idle',
        # title=self.name+" State Diagram",
        # show_conditions=True
        # show_auto_transitions = True,
        finalize_event='finalize'
    )

    
    for key, config in myconfig.get('entities').items():
        _LOGGER.info("Config Item {}: {}".format(str(key), str(config)))
        config["name"] = key
        m = LightingSM(hass, config, machine)
        # machine.add_model(m.model)
        devices.append(m)


    machine.add_transition(trigger='disable',              source='*',                 dest='disabled')

    # Idle
    machine.add_transition(trigger='sensor_off',           source='idle',              dest=None)
    machine.add_transition(trigger='sensor_on',            source='idle',              dest='active',          conditions=['is_state_entities_off'])
    # Disabled      
    machine.add_transition(trigger='enable',               source='disabled',          dest='idle')
    machine.add_transition(trigger='sensor_on',            source='disabled',          dest=None)
    

    machine.add_transition(trigger='sensor_off',           source='disabled',          dest=None)

    machine.add_transition(trigger='enter',                source='active',            dest='active_timer',    unless='will_stay_on')
    machine.add_transition(trigger='enter',                source='active',            dest='active_stay_on',  conditions='will_stay_on')

    # Active Timer
    machine.add_transition(trigger='sensor_on',            source='active_timer',      dest=None,              after='_reset_timer')
    machine.add_transition(trigger='sensor_off',           source='active_timer',      dest=None,              conditions=['is_event_sensor'])
    machine.add_transition(trigger='sensor_off_duration',  source='active_timer',      dest='idle',            conditions=['is_timer_expired'])
    machine.add_transition(trigger='timer_expires',        source='active_timer',      dest='idle',            conditions=['is_event_sensor'])
    machine.add_transition(trigger='timer_expires',        source='active_timer',      dest='idle',            conditions=['is_duration_sensor', 'is_sensor_off'])

    # self.machine.add_transition(trigger='sensor_off', source='active', dest='idle')
    machine.add_transition(trigger='sensor_off',           source='active_stay_on',    dest=None)
    machine.add_transition(trigger='timer_expires',        source='active_stay_on',    dest=None)
    # machine.on_enter_active('on_enter_active')
    # machine.on_enter_idle('on_enter_idle')
    # machine.on_enter_disabled('on_enter_disabled')
    # machine.on_exit_active('on_exit_active')
    # machine.on_exit_idle('on_exit_idle')

    # machine.is_state_entities_off('is_state_entities_off')


    add_devices(devices)
    return True


# import appdaemon.plugins.hass.hassapi as hass
class LightingSM(StateMachine):

    def __init__(self, hass, config, machine):
        # StateMachine.__init__(self, config)
        self.machine = machine
        self.model = Model(hass, config, self)
        

    @property
    def state(self):
        """Return the state of the entity."""
        return self.model.state 
    @property
    def name(self):
        """Return the state of the entity."""
        return self.model.name

    @property
    def state_attributes(self):
        """Return the state of the entity."""

        return {'hello': 'fdfs'}
  

class Model(): # https://dev-docs.home-assistant.io/en/master/api/helpers.html#module-homeassistant.helpers.entity

    

    
    stateEntities = []
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
    machine = None
    entity = None
    stay = False
    def __init__(self, hass, config,entity):
        self.hass = hass
        self.entity =entity

        self.log = logging.getLogger(__name__ + '.' + config.get('name'))
        self.log.setLevel(logging.DEBUG)
        self.log.debug("Init LightingSM with: " + str(config))
        self.name = config.get('name', 'Unnamed Motion Light')
        self.log.debug("Name: " + str(self.name))
        entity.machine.add_model(self) # add here because machine generated methods are being used in methods below.
        self.config_static_strings(config)
        self.config_state_entities(config)
        self.config_control_entities(config) # must come after config_state_entities
        self.config_sensor_entities(config)
        self.config_off_entities(config)
        self.config_normal_mode(config) 
        self.config_night_mode(config) #must come after normal_mode
        self.config_other(config)
        # duration sensor: we want to turn off if:
            # * timer expires. sensor is off
            # * sensor turns off and timer has expired
        # do not turn off if
            # * sensor is on and timer expires
 

    # def draw(self):
    #     self.update()
    #     if self.do_draw:
    #         self.log.debug("Updating graph in state: " + self.state)
    #         self.get_graph().draw(self.image_path + self.image_prefix + str(self.name)+'.png', prog='dot', format='png')


    def update(self, **kwargs):
        self.entity.async_schedule_update_ha_state(True)
        # self.set_state("{}.{}".format(DOMAIN,str(self.name)), state=self.state, attributes=kwargs)

    def finalize(self):
        self.log.debug("state: " + self.state)
        self.entity.async_schedule_update_ha_state(True)

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

        # self.set_state("{}.{}".format(DOMAIN,str(self.name)), state=self.state, attributes=kwargs)
    # =====================================================
    # S T A T E   C H A N G E   C A L L B A C K S
    # =====================================================

    def sensor_state_change(self, entity, old, new):
        self.log.debug("Sensor state change: " + new.state)
        self.log.debug("state: " + self.state)


        if self.matches(new.state, self.SENSOR_ON_STATE):
            self.log.debug("matches on")
            # self.update(last_triggered_by=entity)
            self.sensor_on()
        if self.matches(new.state, self.SENSOR_OFF_STATE) and self.sensor_type == SENSOR_TYPE_DURATION:
            self.log.debug("matches off")
            # self.update(last_triggered_by=entity)
            # We only care about sensor off state changes when the sensor is a duration sensor.
            self.sensor_off_duration()

    def override_state_change(self, entity, old, new):
        if self.matches(new, self.OVERRIDE_ON_STATE):
            # self.update(disabled_by=entity)
            self.disable()
            # self.update(disabled_at=str(datetime.now()))
        if self.matches(new, self.OVERRIDE_OFF_STATE) and not self._override_entity_state():
            self.enable()


    def control_state_change(self, entity, old, new):
        self.log.debug(self.is_active())
        if self.is_active():
            self.control()

    def event_handler(self, event, data, el,**kwargs):
        self.log.debug("Event: " + str(event))
        self.log.debug("Data: " + str(data))
        self.log.debug("kwargs: " + str(el))

        if data['entity_id'] == self.name:
            self.log.debug("It is me!")
            if event == 'lightingsm-reset':
                self.set_state('idle')
                self.log.debug("Reset was called")


    def _start_timer(self):
        self.log.info(self.lightParams)
        if self.backoff_count == 0:
            self.previous_delay = self.lightParams.get('delay', DEFAULT_DELAY)
        else:
            self.log.debug("Backoff: {},  count: {}, delay{}, factor: {}".format(self.backoff,self.backoff_count, self.lightParams.get('delay',DEFAULT_DELAY), self.backoff_factor))
            self.previous_delay = round(self.previous_delay*self.backoff_factor, 2)
            if self.previous_delay > self.backoff_max:
                self.log.debug("Max backoff reached. Will not increase further.")
                self.previous_delay = self.backoff_max

        self.timer_handle = Timer(self.previous_delay, self.timer_expire)
        self.log.debug("Delay: " + str(self.previous_delay))
        self.timer_handle.start()
        expiry_time = str(datetime.now() + timedelta(seconds=self.previous_delay))
        # self.update(delay=self.previous_delay, expires_at=expiry_time)
    
    def _cancel_timer(self):
        if self.timer_handle.is_alive():
            self.timer_handle.cancel()

    def _reset_timer(self):
        self.log.debug("Resetting timer" + str(self.backoff))
        self._cancel_timer()
        if self.backoff:
            self.log.debug("inc backoff")
            self.backoff_count += 1
            # self.update(reset_count=self.backoff_count,reset_at=str(datetime.now()))
        self._start_timer()
        # self.log.debug(str(self.timer_handle))
        return True

       

    # =====================================================
    # S T A T E   M A C H I N E   C O N D I T I O N S
    # =====================================================
    def _override_entity_state(self):
        for e in self.overrideEntities:
            s = self.hass.states.getself.hass.states.get(e)
            self.log.info(s)
            self.log.info(" * State of {} is {}".format(e, s))
            if self.matches(s, self.OVERRIDE_ON_STATE):
                self.log.debug("Override entities are ON. [{}]".format(e))
                return True
        self.log.debug("Override entities are OFF.")
        return False

    def _sensor_entity_state(self):
        for e in self.sensorEntities:
            s = self.hass.states.get(e)
            self.log.info(s)
            self.log.info(" * State of {} is {}".format(e, s))
            if self.matches(s, self.SENSOR_ON_STATE):
                self.log.debug("Sensor entities are ON. [{}]".format(e))
                return True
        self.log.debug("Sensor entities are OFF.")
        return False

    def is_sensor_off(self):
        return self._sensor_entity_state() == False

    def is_sensor_on(self):
        return self._sensor_entity_state()
        
    def _state_entity_state(self):
        for e in self.stateEntities:
            s = self.hass.states.get(e)
            self.log.info(s)
            self.log.debug(" * State of {} is {}".format(e, s))
            if self.matches(s, self.STATE_ON_STATE):
                self.log.debug("State entities are ON. [{}]".format(e))
                return True
        self.log.debug("State entities are OFF.")
        return False
    
    def is_state_entities_off(self):
        return self._state_entity_state() == False

    def is_state_entities_on(self):
        return self._state_entity_state()
    
    def will_stay_on(self):
        return self.stay

    def is_night(self):
        if self.night_mode is None:
            self.log.debug("(night mode disabled): " + str(self.night_mode))
            # self.update(night_mode='on')
            return False
        else:
            # self.update(night_mode='off')
            self.log.debug("NIGHT MODE ENABLED: " + str(self.night_mode))
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
        self.log.debug("is_timer_expired -> " + str(expired))
        return expired
    
    def timer_expire(self):
        # self.log.debug("Timer expired")
        if self.is_duration_sensor():
            self.log.debug("It's a DURATION sensor")
            if self.is_sensor_off():
                self.log.debug("Sensor entities are OFF.")
                self.timer_expires()
        else:    
            self.timer_expires()


    # =====================================================
    # S T A T E   M A C H I N E   C A L L B A C K S
    # =====================================================
    def on_enter_idle(self):
        self.log.debug("Entering idle")
        self.clear_state_attributes()
        # self.draw();

    def on_exit_idle(self):
        self.log.debug("Exiting idle")

    def on_enter_disabled(self):
        self.log.debug("Now disabled")


    def on_enter_active(self):
        # self.update(last_triggered_at=str(datetime.now()))
        self.backoff_count = 0
        if self.is_night():
            self.log.debug("Using NIGHT MODE parameters: " + str(self.light_params_night))
            self.lightParams = self.light_params_night
        else:
            self.log.debug("Using DAY MODE parameters: " + str(self.light_params_day))
            self.lightParams = self.light_params_day

        # self.update(service_data=self.lightParams['service_data'])
        self._start_timer()

        self.log.debug("light params before turning on: " + str(self.lightParams))
        for e in self.controlEntities:
            # self.log.debug("brightness value" + str(self.lightParams.get('brightness')))
            if self.lightParams.get('service_data') is not None:
                self.log.debug("Turning on {} with service parameters {}".format(e, self.lightParams.get('service_data')))
                self.log.debug("Turning on {} with service parameters {}".format(e, self.lightParams.get('service_data')))
                self.hass.services.async_call(e, 'turn_on', self.lightParams.get('service_data'))
            else:
                self.log.debug("Turning on {} (no parameters passed to service call)".format(e))
                self.hass.services.async_call(e, 'turn_on')
        self.enter()


    def on_exit_active(self):
        self.log.debug("Turning off entities, cancelling timer")
        self._cancel_timer() # cancel previous timer


        if self.offEntities is not None:
            self.log.info("using oFF entitesi")
            for e in self.offEntities:
                self.log.info("Turning on {}".format(e))
                
                self.log.debug("Turning on {}".format(e))
                self.turn_on(e)
        else:
            for e in self.controlEntities:
                self.log.debug("Turning off {}".format(e))
                self.turn_off(e)

    
    # =====================================================
    #    C O N F I G U R A T I O N  &  V A L I D A T I O N
    # =====================================================



    def config_control_entities(self, _config):
    
        self.log.debug("Setting up control entities")
        self.controlEntities = []

        if "entity" in _config: # definition of entity tells program to use this entity when checking state (ie. don't use state of entity_on bceause it might be a script.)
            self.controlEntities.append( _config["entity"])

        if "entities" in _config: 
            self.controlEntities.extend( _config['entities'])

        if "entity_on" in _config: 
            self.controlEntities.append( _config["entity_on"] )


        for control in self.controlEntities:
          self.log.debug("Registering control: " + str(control))
          event.async_track_state_change(self.hass, control, self.control_state_change)
        #   self.listen_state(self.control_state_change, control)


        # IF no state entities are defined, use control entites as state
        self.log.debug("State consiion" + str(self.stateEntities))
        if len(self.stateEntities) == 0:
            self.stateEntities.extend(self.controlEntities)
            self.log.debug("Added Control Entities as state entities: " + str(self.stateEntities))
        else:
            self.log.debug("Using existing state entities: " + str(self.stateEntities))
            # self.update(state_entities=self.stateEntities)
        # self.update(control_entities=self.controlEntities)
        self.log.debug("Control Entities: " + str(self.controlEntities))

    def config_state_entities(self, _config):
        
        self.log.info("Setting up state entities")
        if _config.get('state_entities',False): # will control all enti OR the states of all entities and use the result.
            self.log.debug("config defined")
            self.stateEntities = []
            self.stateEntities.extend(_config.get('state_entities',[]))
            # self.update(state_entities=self.stateEntities)
        self.log.info("State Entities: " + str(self.stateEntities))

    def config_off_entities(self, _config):
    
        temp = _config.get("entity_off", None)
        if temp is not None:
            self.log.debug("Setting up off entities")
            self.offEntities = []
            if type(temp) == str:
                self.offEntities.append(temp)
            else:
                self.offEntities.extend(temp)
            # self.update(off_entities=self.offEntities)
            self.log.info('entities: ' + str(self.offEntities))


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
            self.log.debug("No sensor specified, doing nothing")

        self.log.debug("Sensor Entities: " + str(self.sensorEntities))
        # self.update(sensor_entities=self.sensorEntities)

        for sensor in self.sensorEntities:
            self.log.debug("Registering sensor: " + str(sensor))
            event.async_track_state_change(self.hass, sensor, self.sensor_state_change)
            # self.hass.listen_state(self.sensor_state_change, sensor)

    

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
            self.log.info(night_mode)
            self.light_params_night['delay'] = night_mode.get('delay',_config.get("delay", DEFAULT_DELAY))
            self.light_params_night['service_data'] = night_mode.get('service_data',self.light_params_day.get('service_data'))
            self.log.info(self.light_params_night)
            if not "start_time" in night_mode:
                self.log.debug("Night mode requires a start_time parameter !")

            if not "end_time" in night_mode:
                self.log.debug("Night mode requires a end_time parameter !")
            
    def config_normal_mode(self, _config):
        params = {}
        params['delay'] = _config.get("delay", DEFAULT_DELAY)
        params['service_data'] = _config.get("service_data", None)
        self.log.info("serivce data set up: " + str(_config))
        self.light_params_day = params
    def config_other(self, _config):

        self.do_draw = _config.get("draw", False)
        
        if "entity_off" in _config:
            self.entityOff = _config.get("entity_off", None)
       
        self.image_prefix = _config.get('image_prefix','/fsm_diagram_')
        self.image_path = _config.get('image_path','/conf/temp')
        self.backoff = _config.get('backoff', False)
        self.stay = _config.get('stay', False)

        if self.backoff:
            self.log.debug("setting up backoff. Using delay as initial backoff value.")
            self.backoff_factor = _config.get('backoff_factor', 1.1)
            self.backoff_max = _config.get('backoff_max', 300)

        self.stay = _config.get("stay", False)
   
        self.overrideEntities = _config.get("overrides", None)

        if self.overrideEntities is not None:
            for e in self.overrideEntities:
                self.log.info("Setting override callback/s: " + str(e))
                event.async_track_state_change(self.hass, e, self.override_state_change)
                # self.listen_state(self.override_state_change, e)
            # self.update(override_entities=self.overrideEntities)
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


