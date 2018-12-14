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
    ml = SimpleFSM(None, None, None, None, None, None, None, None)
    given_that.time_is(0)
    given_that.passed_arg('image_path').is_set_to(IMAGE_PATH)
    
    return ml


# @pytest.mark.parametrize("entity,entity_value", [
#     ('entity', CONTROL_ENTITY),
#     # ('entities', [CONTROL_ENTITY, CONTROL_ENTITY]),
#     # ('entity_on', CONTROL_ENTITY)
# ])   
@pytest.mark.parametrize("state_entity_value, state_entity_state", [
    (STATE_ENTITY, 'on'),
    ( [SENSOR_ENTITY, SENSOR_ENTITY]),
    # (None)
])  
def test_demo(given_that, ml, assert_that, time_travel,state_entity_value,state_entity_state):
    # given_that.passed_arg(entity).is_set_to(entity_value)
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    given_that.passed_arg('state_entites').is_set_to(state_entity_value)

    given_that.passed_arg('delay').is_set_to(0.001)
    given_that.passed_arg('sensor_type_duration').is_set_to('false')
    given_that.state_of(CONTROL_ENTITY).is_set_to('off')
    given_that.state_of(STATE_ENTITY).is_set_to(state_entity_state) 
    given_that.state_of(CONTROL_ENTITY).is_set_to('off') 
    ml.initialize()
    given_that.mock_functions_are_cleared()
    time.sleep(0.1)


    time_travel.assert_current_time(0).seconds()
    motion(ml)
    time_travel.fast_forward(DELAY).seconds()
    time_travel.assert_current_time(DELAY).seconds()

    assert_that(CONTROL_ENTITY).was.turned_on()
    # ml.timer_expire();
    # time.sleep(2)
    assert_that(CONTROL_ENTITY).was.turned_off()

def test_duration_sensor(given_that, ml, assert_that, time_travel):
    given_that.passed_arg('entity').is_set_to(CONTROL_ENTITY)
    given_that.passed_arg('delay').is_set_to(0.1  )
    given_that.passed_arg('sensor').is_set_to(SENSOR_ENTITY)
    given_that.passed_arg('sensor_type_duration').is_set_to('true')

    given_that.state_of(CONTROL_ENTITY).is_set_to('off')
    ml.initialize()
    given_that.mock_functions_are_cleared()
    time.sleep(0.1)


    time_travel.assert_current_time(0).seconds()
    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)

    assert_that(CONTROL_ENTITY).was.turned_on()
    # ml.timer_expire();
    time.sleep(2)
    given_that.mock_functions_are_cleared(clear_mock_states=True)
    ml.sensor_state_change(SENSOR_ENTITY, None, 'on', 'off', None)
    assert_that(CONTROL_ENTITY).was.turned_off()


    # Helper Functions
def motion(ml):
    ml.sensor_state_change(SENSOR_ENTITY, None, 'off', 'on', None)
    ml.sensor_state_change(SENSOR_ENTITY, None, 'on', 'off', None)
