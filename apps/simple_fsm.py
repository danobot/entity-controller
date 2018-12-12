import appdaemon.plugins.hass.hassapi as hass
from transitions import Machine



# App to turn lights on when motion detected then off again after a delay
class SimpleFSM(hass.Hass):

    
    STATES = ['idle', 'disabled', 'checking', 'active']
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

        self.machine = Machine(model=self, states=SimpleFSM.STATES, initial='idle')
        self.machine.add_transition(trigger='sensor_on', source='idle', dest='disabled', conditions=['is_overridden'])
        self.machine.add_transition(trigger='sensor_on', source='idle', dest='disabled', conditions=['is_overridden'])


        
    # =====================================================
    # S T A T E   M A C H I N E   A C T I O N S
    # =====================================================

    def sensor_state_change(self, entity, attribute, old, new, kwargs):
        if new == self.SENSOR_ON_STATE:
            self.sensor_on()
        if new == self.SENSOR_OFF_STATE:
            self.sensor_off()
    

    def active_entry(self):
        _start_timer();
        _turn_on
    def _start_timer(self):
        return False;
    
    def _reset_timer(self):
        return True;

    
       

    # =====================================================
    # S T A T E   M A C H I N E   C O N D I T I O N S
    # =====================================================
    def _state_entity_state(self):
        return False;
    
    def is_state_entities_off(self):
        return self._state_entity_state() == False;

    def is_state_entities_on(self):
        return self._state_entity_state();

    def is_overridden(self):
        if self.overrideSwitch is None:
            return False;
        else:
            return self.get_state(self.overrideSwitch);




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
