import pytest
from apps.motion_light import MotionLight
# from apps.demo_class import MotionLight

# Important:
# For this example to work, do not forget to copy the `conftest.py` file.
# See README.md for more info
TEST_LIGHT = 'light.test_light';
TEST_SENSOR = 'binary_sensor.test_sensor';
DELAY = 120;
@pytest.fixture
def ml(given_that):
    ml = MotionLight(None, None, None, None, None, None, None, None)
    given_that.passed_arg('__name__').is_set_to('david')
    given_that.passed_arg('delay').is_set_to(DELAY)
    given_that.time_is(0)
    return ml


@pytest.mark.parametrize("entity,entity_value", [
    ('entity', TEST_LIGHT),
    ('entity_on', TEST_LIGHT),
    ('entities', [TEST_LIGHT, TEST_LIGHT])
])    
@pytest.mark.parametrize("state_entity_value", [
    (TEST_SENSOR),
    ( [TEST_SENSOR, TEST_SENSOR]),
    (None)
])    

@pytest.mark.parametrize("sensor,sensor_value", [
    ('sensor',TEST_SENSOR),
    ( 'sensors',[TEST_SENSOR, TEST_SENSOR]),
    (None, None)
]) 
def test_basic(given_that, ml, assert_that, time_travel,entity,entity_value,state_entity_value,sensor,sensor_value):
    given_that.passed_arg(entity).is_set_to(entity_value)
    given_that.passed_arg('state_entites').is_set_to(state_entity_value)
    given_that.passed_arg(sensor).is_set_to(sensor_value)
    # given_that.passed_arg('brightness').is_set_to(brightness)

    ml.initialize()
    given_that.mock_functions_are_cleared()
    given_that.state_of(TEST_LIGHT).is_set_to('off') 
    given_that.state_of(TEST_SENSOR).is_set_to('off') 
    
    time_travel.assert_current_time(0).seconds();

    # Initial Motion
    motion(ml)
    # assert_that('light/turn_on').was.called_with(entity_id=TEST_LIGHT)
    assert_that(TEST_LIGHT).was.turned_on()


    time_travel.fast_forward(DELAY/2).seconds()
    assert_that('light.test_light').was_not.turned_off()

    # New motion
    motion(ml)
    assert_that('light.test_light').was_not.turned_off()
    time_travel.fast_forward(DELAY).seconds()

    # given_that.state_of('light.test_light').is_set_to('on') 

    # After DELAY seconds
    time_travel.assert_current_time(DELAY+DELAY/2).seconds()

    assert_that(TEST_LIGHT).was.turned_off() # light should be turned off





# Helper Functions
def motion(ml):
    ml.motion('binary_sensor.test_sensor', None, 'off', 'on', None)
    ml.motion('binary_sensor.test_sensor', None, 'on', 'off', None)

def motion_with_delay(ml, delay): # For motion sensors that stay on for some duration
    ml.motion('binary_sensor.test_sensor', None, 'off', 'on', None)

    time_travel.fast_forward(delay).seconds()
    ml.motion('binary_sensor.test_sensor', None, 'on', 'off', None)    