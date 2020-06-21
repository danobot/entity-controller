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

# Transition Behaviours
CONF_BEHAVIOURS = 'behaviours'

CONF_ON_ENTER_IDLE='on_enter_idle'
CONF_ON_EXIT_IDLE='on_exit_idle'
CONF_ON_ENTER_ACTIVE='on_enter_active'
CONF_ON_EXIT_ACTIVE='on_exit_active'
CONF_ON_ENTER_OVERRIDDEN = 'on_enter_overidden'
CONF_ON_EXIT_OVERRIDDEN = 'on_exit_overidden'
CONF_ON_ENTER_CONSTRAINED = 'on_enter_constrained'
CONF_ON_EXIT_CONSTRAINED = 'on_exit_constrained'
CONF_ON_ENTER_BLOCKED = 'on_enter_blocked'
CONF_ON_EXIT_BLOCKED = 'on_exit_blocked'

CONF_END_TIME_ACTION = 'end_time_action'
CONF_START_TIME_ACTION = 'start_time_action'
CONF_TRANSITION_BEHAVIOUR_ON = 'on'
CONF_TRANSITION_BEHAVIOUR_OFF = 'off'
CONF_TRANSITION_BEHAVIOUR_IGNORE = 'ignore'
SENSOR_TYPE_DURATION = "duration"
SENSOR_TYPE_EVENT = "event"
MODE_DAY = "day"
MODE_NIGHT = "night"

DEFAULT_DELAY = 180
DEFAULT_BRIGHTNESS = 100
DEFAULT_NAME = "Entity Timer"

# CONF_NAME = 'slug'
CONF_CONTROL_ENTITIES = "entities"
CONF_CONTROL_ENTITY = "entity"
CONF_TRIGGER_ON_ACTIVATE = "trigger_on_activate"
CONF_TRIGGER_ON_DEACTIVATE = "trigger_on_deactivate"
CONF_SENSOR = "sensor"
CONF_SENSORS = "sensors"
CONF_SERVICE_DATA = "service_data"
CONF_SERVICE_DATA_OFF = "service_data_off"
CONF_STATE_ENTITIES = "state_entities"
CONF_DELAY = "delay"
CONF_BLOCK_TIMEOUT = "block_timeout"
CONF_SENSOR_TYPE_DURATION = "sensor_type_duration"
CONF_SENSOR_TYPE = "sensor_type"
CONF_SENSOR_RESETS_TIMER = "sensor_resets_timer"
CONF_NIGHT_MODE = "night_mode"
CONF_STATE_ATTRIBUTES_IGNORE = "state_attributes_ignore"
MODE_DAY = 'day'
MODE_NIGHT = 'night'
CONSTRAIN_START = 1
CONSTRAIN_END = 2
STATES = ['idle', 'overridden', 'constrained', 'blocked',
          {'name': 'active', 'children': ['timer', 'stay_on'],
           'initial': False}]
