import appdaemon.plugins.hass.hassapi as hass
from transitions import Machine
from transitions.extensions import HierarchicalGraphMachine as Machine
import logging
from threading import Timer
import time

VERSION = '0.5.0'
SENSOR_TYPE_DURATION = 1;
SENSOR_TYPE_EVENT = 2;
# App to turn lights on when motion detected then off again after a delay
class LightingSM(hass.Hass):
    
    
    logger = logging.getLogger(__name__)
    STATES = ['idle', 'disabled', {'name': 'active', 'children': [{'name': 'timer','children': ['normal', 'night']},'stay_on'], 'initial': False}]
    stateEntities = None;
    controlEntities = None;
    sensorEntities = None;
    timer_handle = None;
    sensor_type = None;
    night_mode = None;
    backoff = False;
    backoff_count = 0;
    
    def custom_log(self, **kwargs):
        self.logger.error("Callback")
        self.logger.info(kwargs);


    def initialize(self):
        # self.set_app_pin(True);
        # self.listen_log(self.custom_log)
        self.config_state_entities();
        self.config_control_entities();
        self.config_sensor_entities();
        self.config_static_strings();
        self.config_night_mode();
        self.config_other();
        self.machine = Machine(model=self, 
            states=LightingSM.STATES, 
            initial='idle', 
            title=str(__name__)+" State Diagram",
            show_conditions=True,
            # show_auto_transitions = True,
            finalize_event=self.draw
        )
        self.logger.info("Hello")
        # self.log("Drawing graph");
        self.machine.add_transition(trigger='disable', source='*', dest='disabled')

        # Disabled
        self.machine.add_transition(trigger='enable',       source='disabled',          dest='idle')
        self.machine.add_transition(trigger='sensor_on',    source='disabled',          dest=None)
        
        # self.machine.add_transition(trigger='sensor_on', source='idle', dest='checking', unless=['is_overridden'])
        self.machine.add_transition(trigger='sensor_off',   source='idle',              dest=None)
        self.machine.add_transition('sensor_on',            'idle',                     'active',                       conditions=['is_state_entities_off'])

        # self.machine.add_transition(trigger='sensor_on', source='disabled', dest='checking',unless=['is_overridden'])
        self.machine.add_transition(trigger='sensor_off',   source='disabled',          dest='idle')


        self.machine.add_transition(trigger='enter',        source='active',            dest='active_timer',            unless='will_stay_on')
        self.machine.add_transition(trigger='enter',        source='active',            dest='active_stay_on',          conditions='will_stay_on')

        # Active Timer
        self.machine.add_transition(trigger='enter',        source='active_timer',      dest='active_timer_normal',     unless=['is_night'])
        self.machine.add_transition(trigger='enter',        source='active_timer',      dest='active_timer_night',      conditions=['is_night'])
        self.machine.add_transition(trigger='sensor_on',    source='active_timer',      dest=None,                      after='_reset_timer')

        # self.machine.add_transition(trigger='sensor_off', source='active', dest='idle')
        
        # Active Timer Normal
        self.machine.add_transition(trigger='timer_expires', source='active_timer_normal', dest='idle', conditions=['is_event_sensor'])
        self.machine.add_transition(trigger='timer_expires', source='active_timer_normal', dest='idle', conditions=['is_duration_sensor', 'is_sensor_off'])
        self.machine.add_transition(trigger='sensor_off',    source='active_timer_normal', dest=None, conditions=['is_event_sensor'])
        self.machine.add_transition(trigger='sensor_off',    source='active_timer_normal', dest='idle', conditions=['is_duration_sensor','is_timer_expired'])
        # self.machine.add_transition(trigger='timer_expires', source='active_timer_normal', dest='idle', conditions=['is_event_sensor'])
        # self.machine.add_transition(trigger='control',    source='active', dest='idle', before='_cancel_timer')

        # duration sensor: we want to turn off if:
            # * timer expires. sensor is off
            # * sensor turns off and timer has expired
        # do not turn off if
            # * sensor is on and timer expires
    def draw(self):
        self.log("Updating graph in state: " + self.state)
        code = self.get_graph().draw(self.args.get('image_path','/conf/temp') + '/fsm_diagram_'+str(self.name)+'.png', prog='dot', format='png')
        # self.log("Updated graph")

    # =====================================================
    # S T A T E   M A C H I N E   A C T I O N S
    # =====================================================

    def sensor_state_change(self, entity, attribute, old, new, kwargs):
        self.log("Sensor state change")
        if new == self.SENSOR_ON_STATE:
            self.sensor_on()
        if new == self.SENSOR_OFF_STATE:
            if self.sensor_type == SENSOR_TYPE_EVENT:
                self.sensor_off();
              
            #     self.sensor_off_fake()
    
    def override_state_change(self, entity, attribute, old, new, kwargs):
        if new == self.OVERRIDE_ON_STATE:
            self.disable()
        if new == self.OVERRIDE_OFF_STATE:
            self.enable()
    def control_state_change(self, entity, attribute, old, new, kwargs):
        # if new == self.CONTROL_ON_STATE:
        self.log(self.is_active_timer_normal())
        if self.is_active_timer_normal():
            self.control()
        # if new == self.CONTROL_OFF_STATE:
            # self.enable()

    def _start_timer(self):
        if self.backoff_count == 0:
            self.previous_delay = self.delay;
        else:
            self.log("Backoff: {},  count: {}, delay{}, factor: {}".format(self.backoff,self.backoff_count, self.delay, self.backoff_factor))
            self.previous_delay = self.previous_delay*self.backoff_factor
                # delay = 10
            if self.previous_delay > self.backoff_max:
                self.log("Max backoff reached. Will not increase further.")
                self.previous_delay = self.backoff_max
        # 0 - 10
        # 1 - 20

        self.timer_handle = Timer(self.previous_delay, self.timer_expire);
        self.log("Delay: " + str(self.previous_delay));
        self.timer_handle.start();
    
    def _cancel_timer(self):
        if self.timer_handle.is_alive():
            self.timer_handle.cancel();

    def _reset_timer(self):
        self.log("Resetting timer" + str(self.backoff))
        self._cancel_timer();
        if self.backoff:
            self.log("inc backoff");   
            self.backoff_count += 1;
        self._start_timer();
        # self.log(str(self.timer_handle))
        return True;

       

    # =====================================================
    # S T A T E   M A C H I N E   C O N D I T I O N S
    # =====================================================
    def is_sensor_off(self):
        self.log("is sensor off?")
        state = False;
        self.log("Checking sensors: {}".format(str(self.sensorEntities)))
        for e in self.sensorEntities:
            self.log("Sensor check")
            self.logger.info("SEnsor check")
            s = self.get_state(e);
            self.logger.info(s)
            if s == self.SENSOR_OFF_STATE:
                self.logger.info("The sensor is foudn to be on!")
                state = True;
                break;
        self.log(state)
        return state;


    def is_sensor_on(self):
        return self.is_sensor_off() == False;
        
    def _state_entity_state(self):
        state = False;
        for e in self.stateEntities:
            s = self.get_state(e);
            self.log(" * State of {} is {}".format(e, s));
            if s == self.STATE_ON_STATE:
                return True
        return False;
    
    def is_state_entities_off(self):
        return self._state_entity_state() == False;

    def is_state_entities_on(self):
        return self._state_entity_state();
    
    def will_stay_on(self):
        return self.args.get('stay', False);

    def is_night(self):
        if self.night_mode is None:
            return False;
        else:     
            return self.now_is_between(self.night_mode['start_time'], self.night_mode['end_time']);

    def is_event_sensor(self):
        return self.sensor_type == SENSOR_TYPE_EVENT;

    def is_duration_sensor(self):
        return self.sensor_type == SENSOR_TYPE_DURATION;

    def is_timer_expired(self):

        expired = self.timer_handle.is_alive() == False;
        self.log("is timer expired? " + expired)
        return expired;
    
    def timer_expire(self):
        self.log("Timer expired");
        if self.is_duration_sensor():
            self.logger.info("timer expired and its duration")
            if self.is_sensor_off():
                self.logger.info("sensor is off")
                self.timer_expires();

        else:    
            self.timer_expires();
    # =====================================================
    # S T A T E   M A C H I N E   C A L L B A C K S
    # =====================================================
    def on_enter_idle(self):
        self.log("Entering idle")
        # self.draw();

    def on_exit_idle(self):
        self.log("Exiting idle")



    def on_enter_active(self):
        self.enter();
        self.backoff_count = 0;

        # self.draw();
        # _start_timer();
        # turn on entities
        # if will_stay_on():
        #     self.to_active_stay_on();
        # else:
        #     self.to_active_timer();
        self.log("Entering active state. Starting timer and turning on entities.")
        self._start_timer();
        for e in self.controlEntities:
            self.turn_on(e)
    
    def on_enter_active_timer(self):
        self.enter();


    def on_exit_active(self):
        self.log("Turning off entities, cancelling timer");
        self.timer_handle.cancel() # cancel previous timer
        # if self.timer_handle:

        for e in self.controlEntities:
            self.log("Turning off {}".format(e))
            self.turn_off(e)
    def on_enter_disabled(self):
        # self.draw();
        self.log("We are now disabled")

    def on_exit_disabled(self):
        self.log("Leaving disabled")
    
    # def timer_expire(self):

    # def on_enter_checkOverride(self):
    #     if self.is_overridden():
    #         self.to_disabled();
    #     else:
    #         self.to_checking();

    #     self.log(self.state)

    # def on_enter_checking(self):
    #     self.log("Checking state entities")
    #     if self.is_state_entities_off():
    #         self.to_active();
    #     else:
    #         self.to_idle();
    # =====================================================
    #    C O N F I G U R A T I O N  &  V A L I D A T I O N
    # =====================================================



    def config_control_entities(self):
    
        self.log("Setting up control entities")
        self.controlEntities = [];

        if "entity" in self.args: # definition of entity tells program to use this entity when checking state (ie. don't use state of entity_on bceause it might be a script.)
            self.controlEntities.append( self.args["entity"]);

        if "entities" in self.args: 
            self.controlEntities.extend( self.args['entities'])

        if "entity_on" in self.args: 
            self.controlEntities.append( self.args["entity_on"] );


        #for control in self.controlEntities:
        #   self.log("Registering control: " + str(control))
        #   self.listen_state(self.control_state_change, control)


        # IF no state entities are defined, use control entites as state
        if self.stateEntities is  None:
            self.stateEntities = [];
            self.stateEntities.extend(self.controlEntities);
            self.log("Added Control Entities as state entities: " + str(self.stateEntities));
        self.log("Control Entities: " + str(self.controlEntities));

    def config_state_entities(self):
    
        self.log("Setting up state entities")
        if "state_entities" in self.args and self.args['state_entities'] is not None: # will control all enti OR the states of all entities and use the result.
            self.log("config defined")
            self.stateEntities = [];
            self.stateEntities.extend(self.args.get('state_entities',[]));

        self.log("State Entities: " + str(self.stateEntities));


    def config_sensor_entities(self):
        self.sensorEntities = [];
        temp = self.args.get("sensor", None)
        if temp is not None:
            self.sensorEntities.append(temp)
            
        temp = self.args.get("sensors", None)
        if temp is not None:
            self.sensorEntities.extend(temp)


        # self.sensorEntities = [];
        # temp = self.args.get("sensor", [])
        # self.sensorEntities.extend(temp)
            
        # temp = self.args.get("sensors", [])
        # self.sensorEntities.extend(temp)


            
        

        if self.sensorEntities.count == 0:
            self.log("No sensor specified, doing nothing")

        self.log("Sensor Entities: " + str(self.sensorEntities));

        for sensor in self.sensorEntities:
            self.log("Registering sensor: " + str(sensor))
            self.listen_state(self.sensor_state_change, sensor)

    

    def config_static_strings(self):
        self.CONTROL_ON_STATE = self.args.get("control_state_on", "on");
        self.CONTROL_OFF_STATE = self.args.get("control_state_off", "off");
        self.SENSOR_ON_STATE = self.args.get("sensor_state_on", "on");
        self.SENSOR_OFF_STATE = self.args.get("sensor_state_off", "off");
        self.OVERRIDE_ON_STATE = self.args.get("override_state_on", "on");
        self.OVERRIDE_OFF_STATE = self.args.get("override_state_off", "off");
        self.STATE_ON_STATE = self.args.get("state_state_on", "on");
        self.STATE_OFF_STATE = self.args.get("state_state_off", "off");
    def config_night_mode(self):

        # should be implemented by passing nightmore paramters to active_timer state (resuse active_timer state)

        if "night_mode" in self.args:
            self.night_mode = self.args["night_mode"]
            if not "start_time" in self.night_mode:
                self.log("Night mode requires a start_time parameter !")

            if not "end_time" in self.night_mode:
                self.log("Night mode requires a end_time parameter !")
            
    def config_other(self):
        if "entity_off" in self.args:
            self.entityOff = self.args.get("entity_off", None)

        self.delay = self.args.get("delay", 180);
        
        self.backoff = self.args.get('backoff', False)
        if self.backoff:
            self.log("setting up backoff. Using delay as initial backoff value.")
            self.backoff_factor = self.args.get('backoff_factor', 1)
            self.backoff_max = self.args.get('backoff_max', 300)

        self.stay = self.args.get("stay", False)

        if "brightness" in self.args:
            self.brightness = self.args["brightness"]

        self.overrideSwitch = self.args.get("override_switch", None)
        if self.overrideSwitch is not None:
            self.listen_state(self.override_state_change, self.overrideSwitch)
        if self.args.get("sensor_type_duration"):
            self.sensor_type = SENSOR_TYPE_DURATION;
        else:
            self.sensor_type = SENSOR_TYPE_EVENT;

