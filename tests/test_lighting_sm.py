import pytest
import mock
import time as thetime
from datetime import time
from apps.LightingSM import LightingSM
from freezegun import freeze_time
import appdaemon as AppDaemon

CONTROL_ENTITY = 'light.test_light';
CONTROL_ENTITY2 = 'light.test_light2';
CONTROL_ENTITIES = [CONTROL_ENTITY, CONTROL_ENTITY2]
SENSOR_ENTITY = 'binary_sensor.test_sensor';
SENSOR_ENTITY2 = 'binary_sensor.test_sensor2';
SENSOR_ENTITIES = [SENSOR_ENTITY, SENSOR_ENTITY2]
STATE_ENTITY = 'binary_sensor.test_state_entity'
STATE_ENTITY2 = 'binary_sensor.test_state_entity2'
STATE_ENTITIES = [STATE_ENTITY, STATE_ENTITY2]

IMAGE_PATH = '.';
DELAY = 120;

@pytest.fixture
def ml(given_that):
    ml = LightingSM(None, None, None, None, None, None, None, None)
    given_that.time_is(0)
    given_that.passed_arg('image_path').is_set_to(IMAGE_PATH)
    given_that.passed_arg('name').is_set_to('test')
    given_that.passed_arg('draw').is_set_to(True)
    ml.name = 'fds'
    return ml

# @pytest.mark.parametrize("entity,entity_value", [
#     ('entity', CONTROL_ENTITY),
#     # ('entities', [CONTROL_ENTITY, CONTROL_ENTITY]),
#     # ('entity_on', CONTROL_ENTITY)
# ])   
# @pytest.mark.parametrize("state_entity_value, state_entity_state", [
#     (STATE_ENTITY, 'on')
#     # ( [SENSOR_ENTITY, SENSOR_ENTITY]),
#     # (None)
# ])  
def test_basic_config(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')

    ml.initialize()
    given_that.mock_functions_are_cleared()

    assert ml.state == "idle"

    motion(ml)
    assert ml.state == "active_timer"
    assert_that(CONTROL_ENTITY).was.turned_on()
    ml.timer_expire()
    assert ml.state == "idle"
    assert_that(CONTROL_ENTITY).was.turned_off()

def test_basic_config_sad(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    given_that.state_of(CONTROL_ENTITY).is_set_to('on')

    ml.initialize()
    given_that.mock_functions_are_cleared()

    assert ml.state == "idle"

    motion(ml)
    
    assert ml.state == "idle"

    assert_that(CONTROL_ENTITY).was_not.turned_on()

def test_basic_config_stay(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    given_that.passed_arg('stay').is_set_to(True)
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')

    ml.initialize()
    given_that.mock_functions_are_cleared()

    assert ml.state == "idle"

    motion(ml)
    assert ml.state == "active_stay_on"
    assert_that(CONTROL_ENTITY).was.turned_on()
    ml.timer_expire()
    assert ml.state == "active_stay_on"
    assert_that(CONTROL_ENTITY).was_not.turned_off()

def test_basic_duration_happy(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    given_that.passed_arg('sensor_type_duration').is_set_to(True)
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')

    ml.initialize()
    given_that.mock_functions_are_cleared()

    assert ml.state == "idle"

    given_that.state_of(SENSOR_ENTITY).is_set_to('on')
    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)

    assert ml.state == "active_timer"
    assert_that(CONTROL_ENTITY).was.turned_on()


    ml.sensor_state_change(SENSOR_ENTITY, None, 'on', 'off', None)
    # Should stay on because timer has not expired (min timer or sensor)
    assert ml.state == "active_timer"

    given_that.state_of(SENSOR_ENTITY).is_set_to('off')
    given_that.mock_functions_are_cleared()

    ml.timer_expire()
    # should turn off because sensor is off
    assert ml.state == "idle"
    assert_that(CONTROL_ENTITY).was.turned_off()



def test_basic_duration_sad(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    given_that.passed_arg('delay').is_set_to(0.01)
    given_that.passed_arg('sensor_type_duration').is_set_to(True)
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')

    ml.initialize()
    given_that.mock_functions_are_cleared()

    assert ml.state == "idle"

    given_that.state_of(SENSOR_ENTITY).is_set_to('on')
    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)

    assert ml.state == "active_timer"
    assert_that(CONTROL_ENTITY).was.turned_on()

    # no sensor off command is received

    given_that.state_of(SENSOR_ENTITY).is_set_to('on')
    given_that.mock_functions_are_cleared()
    ml.timer_expire()
    # should NOT turn off because sensor is still on
    assert ml.state == "active_timer"
    assert_that(CONTROL_ENTITY).was_not.turned_off()

    ml.timer_expire()
    ml.sensor_state_change(SENSOR_ENTITY, None, 'on', 'off', None)
    
    assert ml.state == "idle"
    # should now turn off because sensor is off
    assert_that(CONTROL_ENTITY).was.turned_off()

    
    
def test_basic_disable(given_that, ml, assert_that, time_travel):
    """
        Tests override switch as well as some custom state strings.
    """
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    given_that.passed_arg('override_states_on').is_set_to(["on",'playing']) # for override only
    given_that.passed_arg('state_strings_off').is_set_to(["off",'idle', 'paused']) # for all
    OVERRIDE_SWITCH='binary_sensor.override'
    OVERRIDE_SWITCH_TV='media_player.tv'
    given_that.passed_arg('overrides').is_set_to([OVERRIDE_SWITCH, OVERRIDE_SWITCH_TV])
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')
    given_that.state_of(OVERRIDE_SWITCH).is_set_to('off')
    given_that.state_of(OVERRIDE_SWITCH_TV).is_set_to('idle')

    ml.initialize()
    given_that.mock_functions_are_cleared()

    assert ml.state == "idle"
    # statechange of override switch should transition to disabled
    ml.override_state_change(OVERRIDE_SWITCH, None, 'off', 'on', None)
    assert ml.state == "disabled"
    motion(ml)
    assert ml.state == "disabled"

    assert_that(CONTROL_ENTITY).was_not.turned_on()

    assert_that(CONTROL_ENTITY).was_not.turned_off()
    ml.override_state_change(OVERRIDE_SWITCH, None, 'on', 'off', None)
    assert ml.state == "idle"

    # same for the other switch
    assert ml.state == "idle"
    # statechange of override switch should transition to disabled
    ml.override_state_change(OVERRIDE_SWITCH, None, 'idle', 'playing', None)
    assert ml.state == "disabled"
    motion(ml)
    assert ml.state == "disabled"

    assert_that(CONTROL_ENTITY).was_not.turned_on()

    assert_that(CONTROL_ENTITY).was_not.turned_off()
    ml.override_state_change(OVERRIDE_SWITCH, None, 'playing', 'paused', None)
    assert ml.state == "idle"

   
def test_control_multiple(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entities').is_set_to(CONTROL_ENTITIES)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')
    given_that.state_of(CONTROL_ENTITY2).is_set_to('off')

    ml.initialize()
    given_that.mock_functions_are_cleared()

   
    assert ml.state == "idle"

    motion(ml)
    assert ml.state == "active_timer"
    assert_that(CONTROL_ENTITY).was.turned_on()
    assert_that(CONTROL_ENTITY2).was.turned_on()
    ml.timer_expire()
    assert ml.state == "idle"
    assert_that(CONTROL_ENTITY).was.turned_off()
    assert_that(CONTROL_ENTITY2).was.turned_off()

    # one control entitiy is on
    given_that.state_of(CONTROL_ENTITY2).is_set_to('on')
    given_that.mock_functions_are_cleared()
    assert ml.state == "idle"

    # should not activate
    motion(ml)

    assert ml.state == "idle"

def test_state_multiple_off(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    given_that.passed_arg('state_entities').is_set_to(STATE_ENTITIES)
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')
    given_that.state_of(STATE_ENTITY).is_set_to('off')
    given_that.state_of(STATE_ENTITY2).is_set_to('off')
    ml.initialize()
    given_that.mock_functions_are_cleared()

   
    assert ml.state == "idle"

    motion(ml)
    assert ml.state == "active_timer"
    assert_that(CONTROL_ENTITY).was.turned_on()
    ml.timer_expire()
    assert ml.state == "idle"
    assert_that(CONTROL_ENTITY).was.turned_off()
   

def test_state_multiple_on(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    given_that.passed_arg('state_entities').is_set_to(STATE_ENTITIES)
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')
    given_that.state_of(STATE_ENTITY).is_set_to('on')
    given_that.state_of(STATE_ENTITY2).is_set_to('off')

    ml.initialize()
    given_that.mock_functions_are_cleared()

   
    assert ml.state == "idle"

    motion(ml)
    
    # should not turn on.

    assert ml.state == "idle"

    # should not activate
    motion(ml)
    assert_that(CONTROL_ENTITY).was_not.turned_on()
    assert ml.state == "idle"

   
def test_sensor_multiple(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('sensors').is_set_to(SENSOR_ENTITIES)
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')
    given_that.state_of(STATE_ENTITY).is_set_to('off')
    given_that.state_of(STATE_ENTITY2).is_set_to('off')
    ml.initialize()
    given_that.mock_functions_are_cleared()

   
    assert ml.state == "idle"

    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)
    ml.sensor_state_change(SENSOR_ENTITY, None, 'on', 'off', None)
    assert ml.state == "active_timer"
    assert_that(CONTROL_ENTITY).was.turned_on()
    ml.timer_expire()
    assert ml.state == "idle"
    assert_that(CONTROL_ENTITY).was.turned_off()

    ml.sensor_state_change(SENSOR_ENTITY2, None, 'off', 'on', None)
    ml.sensor_state_change(SENSOR_ENTITY2, None, 'on', 'off', None)
    assert ml.state == "active_timer"
    assert_that(CONTROL_ENTITY).was.turned_on()
    ml.timer_expire()
    assert ml.state == "idle"
    assert_that(CONTROL_ENTITY).was.turned_off()

def test_complex(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('delay').is_set_to(1)
    given_that.passed_arg('entities').is_set_to(CONTROL_ENTITIES)
    given_that.passed_arg('sensors').is_set_to(SENSOR_ENTITIES)
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')
    given_that.passed_arg('state_entities').is_set_to(STATE_ENTITIES)
    given_that.state_of(STATE_ENTITY).is_set_to('off')
    given_that.state_of(STATE_ENTITY2).is_set_to('off')
    ml.initialize()
    given_that.mock_functions_are_cleared()
    # state entities off
   
    assert ml.state == "idle"

    ml.sensor_state_change(SENSOR_ENTITY, None, 'on', 'off', None)
    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)
    ml.sensor_state_change(SENSOR_ENTITY, None, 'on', 'off', None)
    assert ml.state == "active_timer"
    assert_that(CONTROL_ENTITY).was.turned_on()
    assert_that(CONTROL_ENTITY2).was.turned_on()
    # ml.timer_expire()
    thetime.sleep(2)
    assert ml.state == "idle"
    assert_that(CONTROL_ENTITY).was.turned_off()
    assert_that(CONTROL_ENTITY2).was.turned_off()

    # one control entity is on (should not affect)
    given_that.state_of(CONTROL_ENTITY2).is_set_to('on')
    given_that.mock_functions_are_cleared()

    ml.sensor_state_change(SENSOR_ENTITY2, None, 'off', 'on', None)
    ml.sensor_state_change(SENSOR_ENTITY2, None, 'on', 'off', None)
    assert ml.state == "active_timer"
    assert_that(CONTROL_ENTITY).was.turned_on()
    assert_that(CONTROL_ENTITY2).was.turned_on()

    # motion retriggered on other sensor
    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)
    

    assert_that(CONTROL_ENTITY).was_not.turned_off()
    assert_that(CONTROL_ENTITY2).was_not.turned_off()
    thetime.sleep(2)
    # ml.timer_expire()
    assert ml.state == "idle"
    assert_that(CONTROL_ENTITY).was.turned_off()
    assert_that(CONTROL_ENTITY2).was.turned_off()

    # one state entity is on
    given_that.state_of(STATE_ENTITY2).is_set_to('on')
    given_that.mock_functions_are_cleared()

    ml.sensor_state_change(SENSOR_ENTITY2, None, 'off', 'on', None)
    ml.sensor_state_change(SENSOR_ENTITY2, None, 'on', 'off', None)
    assert ml.state == "idle"
    assert_that(CONTROL_ENTITY).was_not.turned_on()
    assert_that(CONTROL_ENTITY2).was_not.turned_on()
    
def test_backoff(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('delay').is_set_to(4)
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    given_that.passed_arg('backoff').is_set_to(True)
    given_that.passed_arg('backoff_factor').is_set_to(2)
    given_that.passed_arg('backoff_max').is_set_to(10)
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')
    ml.initialize()
    given_that.mock_functions_are_cleared()
    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)

    assert ml.previous_delay == 4
    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)

    assert_that(CONTROL_ENTITY2).was_not.turned_off()
    assert ml.previous_delay == 8
    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)
    assert ml.previous_delay == 10
    assert_that(CONTROL_ENTITY2).was_not.turned_off()

    ml.timer_expire()
    assert_that(CONTROL_ENTITY).was.turned_off()
def test_entity_on_off(given_that, ml, assert_that, time_travel):
    SCRIPT = 'script.entity_off'
    given_that.passed_arg('delay').is_set_to(4)
    given_that.passed_arg('entities').is_set_to(CONTROL_ENTITIES)
    given_that.passed_arg('entity_off').is_set_to(SCRIPT)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
   
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')
    given_that.state_of(CONTROL_ENTITY2).is_set_to('off')
    ml.initialize()
    given_that.mock_functions_are_cleared()
    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)

    assert_that(CONTROL_ENTITY).was.turned_on()
    assert_that(CONTROL_ENTITY2).was.turned_on()

    ml.timer_expire()
    assert_that(CONTROL_ENTITY).was_not.turned_off()
    assert_that(CONTROL_ENTITY2).was_not.turned_off()
    assert_that(SCRIPT).was.turned_on()


def test_parameters_entity(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entity').is_set_to('light.alfred')
    given_that.passed_arg('entity_on').is_set_to('light.dennis')
    given_that.passed_arg('entities').is_set_to(CONTROL_ENTITIES)
    
    given_that.passed_arg('sensor').is_set_to('sensor.jordan')
    given_that.passed_arg('sensors').is_set_to(SENSOR_ENTITIES)

    ml.initialize()
    given_that.mock_functions_are_cleared()
    ml.controlEntities.index('light.dennis') 
    ml.controlEntities.index('light.alfred') 
    ml.controlEntities.index(CONTROL_ENTITY) 
    ml.controlEntities.index(CONTROL_ENTITY2) 
    ml.stateEntities.index('light.dennis') 
    ml.stateEntities.index('light.alfred') 
    ml.stateEntities.index(CONTROL_ENTITY) 
    ml.stateEntities.index(CONTROL_ENTITY2) 
    ml.sensorEntities.index('sensor.jordan') 
    ml.sensorEntities.index(SENSOR_ENTITY) 
    ml.sensorEntities.index(SENSOR_ENTITY2) 

def test_parameters_state(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entities').is_set_to(CONTROL_ENTITIES)
    given_that.passed_arg('state_entities').is_set_to(STATE_ENTITIES)

    ml.initialize()
    given_that.mock_functions_are_cleared()
    ml.controlEntities.index(CONTROL_ENTITY) 
    ml.controlEntities.index(CONTROL_ENTITY2)
    ml.stateEntities.index(STATE_ENTITY) 
    ml.stateEntities.index(STATE_ENTITY2) 

def test_parameters_state_strings(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entities').is_set_to(CONTROL_ENTITIES)
    given_that.passed_arg('state_entities').is_set_to(STATE_ENTITIES)
    given_that.passed_arg('control_states_on').is_set_to(["playing"])
    given_that.passed_arg('state_states_on').is_set_to(["idle"])
    given_that.passed_arg('state_states_off').is_set_to(["not_home"])
    given_that.passed_arg('override_states_on').is_set_to(["off", "paused"])
    given_that.passed_arg('state_strings_on').is_set_to(["hello", "world"])
    given_that.passed_arg('state_strings_off').is_set_to(["hello2", "world2"])

    ml.initialize()
    given_that.mock_functions_are_cleared()

    ml.CONTROL_ON_STATE.index('playing') 
    ml.STATE_ON_STATE.index('idle') 
    ml.OVERRIDE_ON_STATE.index('paused') 

    ml.OVERRIDE_ON_STATE.index('hello') 
    ml.STATE_ON_STATE.index('hello') 
    ml.SENSOR_ON_STATE.index('hello') 

    ml.STATE_OFF_STATE.index('not_home') 

    ml.OVERRIDE_ON_STATE.index('world') 
    ml.STATE_ON_STATE.index('world') 
    ml.CONTROL_ON_STATE.index('world') 
    ml.SENSOR_ON_STATE.index('world') 

    ml.OVERRIDE_OFF_STATE.index('hello2') 
    ml.STATE_OFF_STATE.index('hello2') 
    ml.STATE_OFF_STATE.index('hello2') 
    ml.SENSOR_OFF_STATE.index('hello2') 

    ml.OVERRIDE_OFF_STATE.index('world2') 
    ml.STATE_OFF_STATE.index('world2') 
    ml.CONTROL_OFF_STATE.index('world2') 
    ml.SENSOR_OFF_STATE.index('world2') 

    assert ml.matches("hi", ["hi", "hello"]) == True
    assert ml.matches("bye", ["hi", "hello"]) == False



# @mock.patch('AppDaemon.now_is_between')
def night_mode(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    given_that.passed_arg('hi').is_set_to('treW')
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')
    given_that.state_of(SENSOR_ENTITY).is_set_to('off')
    # mocker.return_value = True
    night = {}
    night['service_data'] = {}
    night['service_data']['brightness']=20
    night['delay']=1
    night['start_time'] ='20:00:00'
    night['end_time'] = '22:00:00'
    given_that.passed_arg('night_mode').is_set_to(night)
    # freezer = freeze_time("19:00:00")
    # freezer.start()
    given_that.time_is(time(hour=19))

    ml.initialize()
    given_that.mock_functions_are_cleared()

    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)
    ml.sensor_state_change(SENSOR_ENTITY, None, 'on', 'off', None)
    

    assert_that(CONTROL_ENTITY).was.turned_on(brightness=98)
    assert ml.previous_delay == 180
    # freezer.stop()
    given_that.time_is(time(hour=21))
    # freezer = freeze_time("21:00:00")
    # freezer.start()
    given_that.mock_functions_are_cleared()
    

    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)
    ml.sensor_state_change(SENSOR_ENTITY, None, 'on', 'off', None)

    assert ml.previous_delay == 20
    assert ml.lightParams['delay'] == 1
    


    assert_that(CONTROL_ENTITY).was.turned_on(brightness=20)



# Helper Functions
def motion(ml):
    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)
    ml.sensor_state_change(SENSOR_ENTITY, None, 'on', 'off', None)
