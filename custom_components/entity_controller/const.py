""" Constants used by other files """

DOMAIN = "entity_controller"

# services
SERVICE_CLEAR_BLOCK = "clear_block"
SERVICE_SET_STAY_ON = "set_stay_on"
SERVICE_SET_STAY_OFF = "set_stay_off"
SERVICE_SET_NIGHT_MODE = "set_night_mode"

#configuration
CONF_START_TIME = 'start_time'
CONF_END_TIME = 'end_time'

MODE_DAY = 'day'
MODE_NIGHT = 'night'

STATES = ['idle', 'overridden', 'constrained', 'blocked',
          {'name': 'active', 'children': ['timer', 'stay_on'],
           'initial': False}]
