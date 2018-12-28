import pytest

from apps.demo_class import MotionLight

# Important:
# For this example to work, do not forget to copy the `conftest.py` file.
# See README.md for more info
TEST_LIGHT = 'light.test_light';
TEST_SENSOR = 'binary_sensor.test_sensor';
DELAY = 120;
@pytest.fixture
def motion_light(given_that):
    motion_light = MotionLight(None, None, None, None, None, None, None, None)
    given_that.time_is(0)
    motion_light.initialize()
    given_that.mock_functions_are_cleared()
    return motion_light


def test_demo(given_that, motion_light, assert_that, time_travel):
    given_that.state_of('light.test_light').is_set_to('on') 
    time_travel.assert_current_time(0).seconds()
    motion_light.motion(DELAY)
    time_travel.fast_forward(DELAY).seconds()
    time_travel.assert_current_time(DELAY).seconds()
    assert_that('light.test_light').was.turned_off()