import pytest

from apps.simple_fsm import SimpleFSM

# Important:
# For this example to work, do not forget to copy the `conftest.py` file.
# See README.md for more info
TEST_LIGHT = 'light.test_light';
TEST_SENSOR = 'binary_sensor.test_sensor';
DELAY = 120;

@pytest.fixture
def ml(given_that):
    ml = SimpleFSM(None, None, None, None, None, None, None, None)
    given_that.time_is(0)
    ml.initialize()
    given_that.mock_functions_are_cleared()
    return ml


def test_demo(given_that, ml, assert_that, time_travel):
    given_that.state_of('light.test_light').is_set_to('off') 
    time_travel.assert_current_time(0).seconds()
    motion(ml)
    time_travel.fast_forward(DELAY).seconds()
    time_travel.assert_current_time(DELAY).seconds()
    assert_that('light.test_light').was.turned_off()


    # Helper Functions
def motion(ml):
    ml.sensor_state_change('binary_sensor.test_sensor', None, 'off', 'on', None)
    ml.sensor_state_change('binary_sensor.test_sensor', None, 'on', 'off', None)
