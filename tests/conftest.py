import pytest
from appdaemontestframework import patch_hass, AssertThatWrapper, GivenThatWrapper, TimeTravelWrapper


@pytest.fixture
def hass_functions():
    patched_hass_functions, unpatch_callback = patch_hass()
    yield patched_hass_functions
    unpatch_callback()


@pytest.fixture
def given_that(hass_functions):
    return GivenThatWrapper(hass_functions)


@pytest.fixture
def assert_that(hass_functions):
    return AssertThatWrapper(hass_functions)


@pytest.fixture
def time_travel(hass_functions):
    return TimeTravelWrapper(hass_functions)