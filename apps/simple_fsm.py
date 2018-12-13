import appdaemon.plugins.hass.hassapi as hass
from transitions import Machine
from transitions.extensions import HierarchicalGraphMachine as Machine
import logging

logging.getLogger('transitions').setLevel(logging.INFO)
# App to turn lights on when motion detected then off again after a delay
class SimpleFSM(hass.Hass):

    
    STATES = ['idle', 'disabled', 'active']
    stateEntities = None;
    controlEntities = None;
    sensorEntities = None;
    delay = 180 # default delay = 3 minutes

    def initialize(self):
        self.timer = None
        self.config_control_entities();
        self.config_state_entities();
        self.config_sensor_entities();
        self.config_static_strings();
        self.config_other();
        self.machine = Machine(model=self, 
            states=SimpleFSM.STATES, 
            initial='idle', 
            title=str(__name__)+" State Diagram",
            show_conditions=True,
            show_auto_transitions =True,
            after_state_change=self.draw
        )

        self.log("Drawing graph");
        self.machine.add_transition(trigger='sensor_on', source='idle', dest='disabled', conditions='is_overridden')
        # self.machine.add_transition(trigger='sensor_on', source='idle', dest='checking', unless=['is_overridden'])
        self.machine.add_transition(trigger='sensor_off', source='idle', dest=None)

        # self.machine.add_transition(trigger='sensor_on', source='disabled', dest='checking',unless=['is_overridden'])
        self.machine.add_transition(trigger='sensor_off', source='disabled', dest=None)

        self.machine.add_transition('sensor_on', ['idle', 'disabled'], 'active',conditions=['is_state_entities_off']) # , unless=[ 'is_overridden']


        self.machine.add_transition(trigger='sensor_off', source='active', dest='idle')
        # self.machine.add_transition(trigger='sensor_on', source='active', dest='=')
        self.machine.add_transition(trigger='timer_expires', source='active', dest='idle')


    def draw(self):
        self.log("Updating graph")
        code = self.get_graph().draw('/conf/temp/fsm_diagram_'+str(__name__)+'.png', prog='dot', format='png')
        self.log("Updated graph: " + str(code))

    # =====================================================
    # S T A T E   M A C H I N E   A C T I O N S
    # =====================================================

    def sensor_state_change(self, entity, attribute, old, new, kwargs):
        if new == self.SENSOR_ON_STATE:
            self.sensor_on()
        if new == self.SENSOR_OFF_STATE:
            self.sensor_off()
    


    def _start_timer(self):
        return False;
    
    def _reset_timer(self):
        return True;

    
       

    # =====================================================
    # S T A T E   M A C H I N E   C O N D I T I O N S
    # =====================================================
    def _state_entity_state(self):
        for e in self.stateEntities:
            state = True;
            s = self.get_state(e);
            state = state or s == self.ON_STATE;
            self.log(" * State of {} is {} and cumulative state is {}".format(e, s, state));
        return state;
    
    def is_state_entities_off(self):
        return self._state_entity_state() == True;

    def is_state_entities_on(self):
        return self._state_entity_state();

    def is_overridden(self):
        self.log("is_overridden" + self.overrideSwitch)
        if self.overrideSwitch is None:
            self.log("is_overridden: false")
            return False;
        else:
            self.log("is_overridden: " + self.get_state(self.overrideSwitch))
            return self.get_state(self.overrideSwitch) == self.OVERRIDE_ON_STATE;
    

    # =====================================================
    # S T A T E   M A C H I N E   C A L L B A C K S
    # =====================================================
    def on_enter_idle(self):
        self.log("Entering idle")
        # self.draw();

    def on_exit_idle(self):
        self.log("Exiting idle")
    def timer_expire(self):
        self.timer_expires();
    def on_enter_active(self):
        # self.draw();
        # _start_timer();
        # turn on entities
        self.log("Entering active state. Starting timer and turning on entities.")
        self.timer_handle = self.run_in(self.timer_expires, 2)
        for e in self.controlEntities:
            self.turn_on(e)
        
    def on_exit_active(self):
        self.log("Turning off entities, cancelling timer");
        if self.timer_handle:
            self.cancel_timer(self.timer) # cancel previous timer
        for e in self.controlEntities:
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
    
        self.controlEntities = [];

        if "entity" in self.args: # definition of entity tells program to use this entity when checking state (ie. don't use state of entity_on bceause it might be a script.)
            self.controlEntities.append( self.args["entity"]);
            self.stateEntities = self.controlEntities
        elif "entities" in self.args: 
            self.controlEntities.append( self.args['entities'])
        # else:
        #     self.controlEntities.append(self.args["entity_on"] );

        self.log("Control Entities: " + str(self.controlEntities));

    def config_state_entities(self):
    

        if "state_entities" in self.args: # will control all enti OR the states of all entities and use the result.
            self.stateEntities = [];
            self.stateEntities = self.args['state_entities']

        self.log("State Entities: " + str(self.stateEntities));

    def config_sensor_entities(self):
        self.sensorEntities = [];
        temp = self.args.get("sensor", None)
        if temp is not None:
            self.sensorEntities.append(temp)
            
        temp = self.args.get("sensors", None)
        if temp is not None:
            self.sensorEntities.extend(temp)


            
        

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

    def config_other(self):
        if "entity_off" in self.args:
            self.entityOff = self.args.get("entity_off", None)

        if "delay" in self.args:
            self.delay = self.args["delay"]

        if "stay" in self.args:
            self.stay = self.args["stay"]

        if "brightness" in self.args:
            self.brightness = self.args["brightness"]

        self.overrideSwitch = self.args.get("override_switch", None)
