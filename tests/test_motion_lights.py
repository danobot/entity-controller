import pytest
from apps.motion_light import MotionLight

# Important:
# For this example to work, do not forget to copy the `conftest.py` file.
# See README.md for more info
TEST_LIGHT = 'light.test_light';
TEST_SENSOR = 'binary_sensor.test_sensor';
@pytest.fixture
def motion_light(given_that):
    motion_light = MotionLight(None, None, None, None, None, None, None, None)
    given_that.passed_arg('entity').is_set_to(TEST_LIGHT)
    given_that.passed_arg('sensor').is_set_to(TEST_SENSOR)
    given_that.passed_arg('__name__').is_set_to('david')
    motion_light.initialize()
    given_that.mock_functions_are_cleared()
    return motion_light


def test_basic(given_that, motion_light, assert_that):
    given_that.state_of('light.test_light').is_set_to('off') 
    given_that.state_of(TEST_SENSOR).is_set_to('off') 
    

    motion_light.motion('binary_sensor.test_sensor', None, 'off', 'on', None)
    given_that.state_of(TEST_SENSOR).is_set_to('on') 
    # assert_that('light/turn_on').was.called_with(entity_id=TEST_LIGHT)
    assert_that(TEST_LIGHT).was.turned_on()
