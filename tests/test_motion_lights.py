import pytest
from apps.motion_light import MotionLight

# Important:
# For this example to work, do not forget to copy the `conftest.py` file.
# See README.md for more info

@pytest.fixture
def motion_light(given_that):
    motion_light = MotionLight(None, None, None, None, None, None, None, None)
    given_that.passed_arg('entity').is_set_to('light.test_light')
    given_that.passed_arg('sensor').is_set_to('binary_sensor.test_sensor')
    motion_light.initialize()
    given_that.mock_functions_are_cleared()
    return motion_light


def test_during_night_light_turn_on(given_that, motion_light, assert_that):
    given_that.state_of('light.test_light').is_set_to('off') 
    

    motion_light.motion(None, None, None, None, None)
    assert_that('light.test_light').was.turned_on()
