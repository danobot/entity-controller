import pytest
import time
from apps.LightingSM import LightingSM

# Important:
# For this example to work, do not forget to copy the `conftest.py` file.
# See README.md for more info
CONTROL_ENTITY = 'light.test_light';
CONTROL_ENTITY2 = 'light.test_light2';
SENSOR_ENTITY = 'binary_sensor.test_sensor';
CONTROL_ENTITIES = [CONTROL_ENTITY, CONTROL_ENTITY2]
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
    assert ml.state == "active_timer_normal"
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

    assert ml.state == "active_timer_normal"
    assert_that(CONTROL_ENTITY).was.turned_on()


    ml.sensor_state_change(SENSOR_ENTITY, None, 'on', 'off', None)
    # Should stay on because timer has not expired (min timer or sensor)
    assert ml.state == "active_timer_normal"

    given_that.state_of(SENSOR_ENTITY).is_set_to('off')
    ml.timer_expire()
    # should turn off because sensor is off
    assert ml.state == "idle"
    assert_that(CONTROL_ENTITY).was.turned_off()


def test_basic_duration_sad(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    given_that.passed_arg('sensor_type_duration').is_set_to(True)
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')

    ml.initialize()
    given_that.mock_functions_are_cleared()

    assert ml.state == "idle"

    given_that.state_of(SENSOR_ENTITY).is_set_to('on')
    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)

    assert ml.state == "active_timer_normal"
    assert_that(CONTROL_ENTITY).was.turned_on()

    # no sensor off command is received

    given_that.state_of(SENSOR_ENTITY).is_set_to('on')
    ml.timer_expire()
    # should NOT turn off because sensor is still on
    assert ml.state == "active_timer_normal"
    assert_that(CONTROL_ENTITY).was_not.turned_off()
    
def test_basic_disable(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    OVERRIDE_SWITCH='binary_sensor.override'
    given_that.passed_arg('override_switch').is_set_to(OVERRIDE_SWITCH)
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')
    given_that.state_of(OVERRIDE_SWITCH).is_set_to('off')

    ml.initialize()
    given_that.mock_functions_are_cleared()

    assert ml.state == "idle"
    # statechange of override switch should transition to disabled
    ml.override_state_change(OVERRIDE_SWITCH, None, 'off', 'on', None)
    assert ml.state == "disabled"
    motion(ml)
    assert ml.state == "disabled"

    assert_that(CONTROL_ENTITY).was_not.turned_on()

    assert ml.state == "disabled"
    assert_that(CONTROL_ENTITY).was_not.turned_off()
    ml.override_state_change(OVERRIDE_SWITCH, None, 'on', 'off', None)
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
    assert ml.state == "active_timer_normal"
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

   
# Helper Functions
def motion(ml):
    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)
    ml.sensor_state_change(SENSOR_ENTITY, None, 'on', 'off', None)
