import pytest
import time
from apps.LightingSM import LightingSM

# Important:
# For this example to work, do not forget to copy the `conftest.py` file.
# See README.md for more info
CONTROL_ENTITY = 'light.test_light';
SENSOR_ENTITY = 'binary_sensor.test_sensor';

STATE_ENTITY = 'binary_sensor.test_state_entity'

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
# Helper Functions
def motion(ml):
    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)
    ml.sensor_state_change(SENSOR_ENTITY, None, 'on', 'off', None)
