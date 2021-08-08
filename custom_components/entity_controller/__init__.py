"""
This file is part of Entity Controller.

Entity Controller is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Entity Controller is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Entity Controller.  If not, see <https://www.gnu.org/licenses/>.

"""
"""
Entity controller component for Home Assistant.
Maintainer:       Daniel Mason
Version:          v9.2.9
Project Page:     https://danielbkr.net/projects/entity-controller/
Documentation:    https://github.com/danobot/entity-controller
"""
import hashlib
import logging
import re
from datetime import date, datetime, time, timedelta
from threading import Timer
import pprint
from typing import Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_NAME, SUN_EVENT_SUNRISE, SUN_EVENT_SUNSET
from homeassistant.core import callback, Context
from homeassistant.helpers import entity, event, service
from homeassistant.helpers.template import Template
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.sun import get_astral_event_date
from homeassistant.util import dt
import homeassistant.util.uuid as uuid_util
from transitions import Machine
from transitions.extensions import HierarchicalMachine as Machine
from homeassistant.helpers.service import async_call_from_config

DEPENDENCIES = ["light", "sensor", "binary_sensor", "cover", "fan", "media_player"]
from .const import (
    DOMAIN,
    DOMAIN_SHORT,
    STATES,

    CONF_START_TIME,
    CONF_END_TIME,
    CONF_TRANSITION_BEHAVIOUR_ON,
    CONF_TRANSITION_BEHAVIOUR_OFF,
    CONF_TRANSITION_BEHAVIOUR_IGNORE,

    # Behaviours
    CONF_BEHAVIOURS,
    CONF_ON_ENTER_IDLE,
    CONF_ON_EXIT_IDLE,
    CONF_ON_ENTER_ACTIVE,
    CONF_ON_EXIT_ACTIVE,
    CONF_ON_ENTER_OVERRIDDEN,
    CONF_ON_EXIT_OVERRIDDEN,
    CONF_ON_ENTER_CONSTRAINED,
    CONF_ON_EXIT_CONSTRAINED,
    CONF_ON_ENTER_BLOCKED,
    CONF_ON_EXIT_BLOCKED,

    SENSOR_TYPE_DURATION,
    SENSOR_TYPE_EVENT,
    MODE_DAY,
    MODE_NIGHT,
    DEFAULT_DELAY,
    DEFAULT_BRIGHTNESS,
    DEFAULT_NAME,
    CONF_CONTROL_ENTITIES,
    CONF_CONTROL_ENTITY,
    CONF_TRIGGER_ON_ACTIVATE,
    CONF_TRIGGER_ON_DEACTIVATE,
    CONF_SENSOR,
    CONF_SENSORS,
    CONF_SERVICE_DATA,
    CONF_SERVICE_DATA_OFF,
    CONF_STATE_ENTITIES,
    CONF_DELAY,
    CONF_BLOCK_TIMEOUT,
    CONF_SENSOR_TYPE_DURATION,
    CONF_SENSOR_TYPE,
    CONF_SENSOR_RESETS_TIMER,
    CONF_NIGHT_MODE,
    CONF_STATE_ATTRIBUTES_IGNORE,
    CONF_IGNORED_EVENT_SOURCES,
    CONSTRAIN_START,
    CONSTRAIN_END,

    CONTEXT_ID_CHARACTER_LIMIT
)

from .entity_services import (
    async_setup_entity_services,
)



VERSION = '9.2.9'


_LOGGER = logging.getLogger(__name__)

devices = []
MODE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SERVICE_DATA, default=None): vol.Coerce(
            dict
        ),  # Default must be none because we differentiate between set and unset
        vol.Optional(CONF_SERVICE_DATA_OFF, default=None): vol.Coerce(dict),
        vol.Required(CONF_START_TIME): cv.string,
        vol.Required(CONF_END_TIME): cv.string,
        vol.Optional(CONF_DELAY, default=DEFAULT_DELAY): cv.positive_int,
    }
)

ENTITY_SCHEMA = vol.Schema(
    cv.has_at_least_one_key(
        CONF_CONTROL_ENTITIES, CONF_CONTROL_ENTITY, CONF_TRIGGER_ON_ACTIVATE
    ),
    {
        # vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_DELAY, default=DEFAULT_DELAY): cv.positive_int,
        vol.Optional(CONF_START_TIME): cv.string,
        vol.Optional(CONF_END_TIME): cv.string,
        vol.Optional(CONF_SENSOR_TYPE_DURATION, default=False): cv.boolean,
        vol.Optional(CONF_SENSOR_TYPE, default=SENSOR_TYPE_EVENT): vol.All(
            vol.Lower, vol.Any(SENSOR_TYPE_EVENT, SENSOR_TYPE_DURATION)
        ),
        vol.Optional(CONF_SENSOR_RESETS_TIMER, default=False): cv.boolean,
        vol.Optional(CONF_SENSOR, default=[]): cv.entity_ids,
        vol.Optional(CONF_SENSORS, default=[]): cv.entity_ids,
        vol.Optional(CONF_CONTROL_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(CONF_CONTROL_ENTITY, default=[]): cv.entity_ids,
        vol.Optional(CONF_TRIGGER_ON_ACTIVATE, default=None): cv.entity_ids,
        vol.Optional(CONF_TRIGGER_ON_DEACTIVATE, default=None): cv.entity_ids,
        vol.Optional(CONF_STATE_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(CONF_BLOCK_TIMEOUT, default=None): cv.positive_int,
        # vol.Optional(CONF_IGNORE_STATE_CHANGES_UNTIL, default=None): cv.positive_int,
        vol.Optional(CONF_NIGHT_MODE, default=None): MODE_SCHEMA,
        vol.Optional(CONF_STATE_ATTRIBUTES_IGNORE, default=[]): cv.ensure_list,
        vol.Optional(CONF_IGNORED_EVENT_SOURCES, default=[]): cv.ensure_list,
        vol.Optional(CONF_SERVICE_DATA, default=None): vol.Coerce(
            dict
        ),
        vol.Optional(CONF_BEHAVIOURS, default=None): vol.Coerce(
            dict
        ),
        # Default must be none because we differentiate between set and unset
        vol.Optional(CONF_SERVICE_DATA_OFF, default=None): vol.Coerce(dict),
    },
    # extra=vol.ALLOW_EXTRA,
)

PLATFORM_SCHEMA = cv.schema_with_slug_keys(ENTITY_SCHEMA)


async def async_setup(hass, config):
    """Load graph configurations."""

    component = EntityComponent(_LOGGER, DOMAIN, hass)

    _LOGGER.info(
        "If you have ANY issues with EntityController (v"
        + VERSION
        + "), please enable DEBUG logging under the logger component and kindly report the issue on Github. https://github.com/danobot/entity-controller/issues"
    )

    async_setup_entity_services(component)

    machine = Machine(
        states=STATES,
        initial="idle",
        # title=self.name+" State Diagram",
        # show_conditions=True
        # show_auto_transitions = True,
        finalize_event="finalize",
    )

    machine.add_transition(trigger="constrain", source="*", dest="constrained")
    machine.add_transition(
        trigger="override",
        source=["idle", "active_timer", "blocked"],
        dest="overridden",
    )

    # Idle
    # machine.add_transition(trigger='sensor_off',           source='idle',              dest=None)
    machine.add_transition(
        trigger="sensor_on",
        source="idle",
        dest="active",
        conditions=["is_state_entities_off"],
    )
    machine.add_transition(
        trigger="sensor_on",
        source="idle",
        dest="blocked",
        conditions=["is_state_entities_on"],
    )
    machine.add_transition(trigger="enable", source="idle", dest=None, conditions=["is_state_entities_off"])

    # Blocked
    machine.add_transition(trigger="enable", source="blocked", dest="idle", conditions=["is_state_entities_off"])
    machine.add_transition(
        trigger="sensor_on", source="blocked", dest="blocked"
    )  # re-entering self-transition (on_enter callback executed.)

    # Overridden
    # machine.add_transition(trigger='enable', source='overridden', dest='idle')
    machine.add_transition(
        trigger="enable",
        source="overridden",
        dest="idle",
        conditions=["is_state_entities_off"],
    )
    # If a device leaving overridden is on, we do not necessarily want to shut it off immediately. We simply want EC to stop controlling it. To do that, we'll move it to active, to simulate an EC trigger, and we'll see if it exits on its own. This works for event sensors, of course, and it will also work for duration sensors if the current state is on. A duration sensor that is off now will never expire on its own, though, so in that case, we'll assume the target is 'idle'.
    machine.add_transition(
        trigger="enable",
        source="overridden",
        dest="active",
        conditions=["is_state_entities_on", "is_event_sensor"],
    )
    machine.add_transition(
        trigger="enable",
        source="overridden",
        dest="active",
        conditions=["is_state_entities_on", "is_sensor_on"],
    )  # This could be duration && on, but it will also work for any event sensor, so it's simpler to just write 'on'
    machine.add_transition(
        trigger="enable",
        source="overridden",
        dest="idle",
        conditions=["is_state_entities_on", "is_duration_sensor", "is_sensor_off"],
    )


    machine.add_transition(
        trigger="enter", source="active", dest="active_timer", unless="will_stay_on"
    )
    machine.add_transition(
        trigger="enter",
        source="active",
        dest="active_stay_on",
        conditions="will_stay_on",
    )

    # Active Timer
    machine.add_transition(
        trigger="sensor_on", source="active_timer", dest=None, after="_reset_timer"
    )
    # machine.add_transition(trigger='sensor_off',           source='active_timer',      dest=None,              conditions=['is_event_sensor'])
    machine.add_transition(
        trigger="sensor_off_duration",
        source="active_timer",
        dest="idle",
        conditions=["is_timer_expired"],
    )
    # The following two transitions must be kept seperate because they have
    # special conditional logic that cannot be combined.
    machine.add_transition(
        trigger="timer_expires",
        source="active_timer",
        dest="idle",
        conditions=["is_event_sensor"],
    )
    machine.add_transition(
        trigger="timer_expires",
        source="active_timer",
        dest="idle",
        conditions=["is_duration_sensor", "is_sensor_off"],
    )
    # machine.add_transition(trigger='block_timer_expires', source='blocked', dest='idle')
    machine.add_transition(
        trigger="block_timer_expires",
        source="blocked",
        dest="active",
        conditions=["is_state_entities_on", "is_event_sensor"],
    )
    machine.add_transition(
        trigger="block_timer_expires",
        source="blocked",
        dest="active",
        conditions=["is_state_entities_on", "is_sensor_on"],
    )  # This could be duration && on, but it will also work for any event sensor, so it's simpler to just write 'on'
    machine.add_transition(
        trigger="block_timer_expires",
        source="blocked",
        dest="idle",
        conditions=["is_state_entities_on", "is_duration_sensor", "is_sensor_off"],
    )

    # Active Timer
    machine.add_transition(
        trigger="control",
        source="active_timer",
        dest="idle",
        conditions=["is_state_entities_off"]
    )
    machine.add_transition(trigger='control', source='active_timer',
                           dest='blocked', conditions=['is_state_entities_on'])

    # machine.add_transition(trigger='sensor_off',           source='active_stay_on',    dest=None)
    # machine.add_transition(trigger="timer_expires", source="active_stay_on", dest=None)
    machine.add_transition(
        trigger="enable",
        source="active_stay_on",
        dest="idle",
        conditions=["is_state_entities_off"]
    )
    # Constrained
    machine.add_transition(
        trigger="enable",
        source="constrained",
        dest="idle",
        conditions=["is_override_state_off"],
    )
    machine.add_transition(
        trigger="enable",
        source="constrained",
        dest="overridden",
        conditions=["is_override_state_on"],
    )
    # Enter blocked state when component is enabled and entity is on
    machine.add_transition(trigger="blocked", source="constrained", dest="blocked")

    for myconfig in config[DOMAIN]:
        _LOGGER.info("Domain Configuration: " + str(myconfig))
        for key, config in myconfig.items():
            if not config:
                config = {}

            # _LOGGER.info("Config Item %s: %s", str(key), str(config))
            config["name"] = key
            m = None
            m = EntityController(hass, config, machine)
            # machine.add_model(m.model)
            # m.model.after_model(config)
            devices.append(m)

    await component.async_add_entities(devices)

    _LOGGER.info("The %s component is ready!", DOMAIN)

    return True


class EntityController(entity.Entity):
    from .entity_services import (
        async_entity_service_clear_block as async_clear_block,
        async_entity_service_enable_stay_mode as async_enable_stay_mode,
        async_entity_service_disable_stay_mode as async_disable_stay_mode,
        async_entity_service_set_night_mode as async_set_night_mode,
    )

    def __init__(self, hass, config, machine):
        self.attributes = {}
        self.may_update = False
        self.model = None
        self.friendly_name = config.get(CONF_NAME, "Motion Light")
        if "friendly_name" in config:
            self.friendly_name = config.get("friendly_name")
        try:
            self.model = Model(hass, config, machine, self)
        except AttributeError as e:
            _LOGGER.error(
                "Configuration error! Please ensure you use plural keys for lists. e.g. sensors, entities." + e
            )
        event.async_call_later(hass, 1, self.do_update)

    @property
    def state(self):
        """Return the state of the entity."""
        return self.model.state

    @property
    def name(self):
        """Return the state of the entity."""
        return self.friendly_name

    @property
    def icon(self):
        """Return the entity icon."""
        if self.model.state == "idle":
            return "mdi:circle-outline"
        if self.model.state == "active":
            return "mdi:check-circle"
        if self.model.state == "active_timer":
            return "mdi:timer-outline"
        if self.model.state == "constrained":
            return "mdi:cancel"
        if self.model.state == "overridden":
            return "mdi:timer-off-outline"
        if self.model.state == "blocked":
            return "mdi:close-circle"
        return "mdi:eye"

    @property
    def state_attributes(self):
        """Return the state of the entity."""
        return self.attributes.copy()

    def reset_state(self):
        """ Reset state attributes by removing any state specific attributes when returning to idle state """
        _LOGGER.debug("Resetting state")
        att = {}

        PERSISTED_STATE_ATTRIBUTES = [
            "last_triggered_by",
            "last_triggered_at",
            CONF_STATE_ENTITIES,
            "control_entities",
            "sensor_entities",
            "override_entities",
            CONF_DELAY,
            "sensor_type",
            "mode",
            "start_time",
            "end_time",
        ]
        for k, v in self.attributes.items():
            if k in PERSISTED_STATE_ATTRIBUTES:
                att[k] = v

        self.attributes = att
        self.do_update()

    @callback
    def do_update(self, wait=False, **kwargs):
        """ Schedules an entity state update with HASS """
        # _LOGGER.debug("Scheduled update with HASS")
        if self.may_update:
            self.async_schedule_update_ha_state(True)

    def set_attr(self, k, v):
        if k == CONF_DELAY:
            v = str(v) + "s"
        self.attributes[k] = v

    # HA Callbacks
    async def async_added_to_hass(self):
        """Register update dispatcher."""
        self.may_update = True

    @property
    def should_poll(self) -> bool:
        """EntityController will push its state to HA"""
        return False

class Model:
    """ Represents the transitions state machine model """

    def __init__(self, hass, config, machine, entity):
        self.hass = hass  # backwards reference to hass object
        self.entity = entity  # backwards reference to entity containing this model

        self.config = (
            {}
        )  # new way of storing configuration (avoids having an attribue for each)
        self.config = config
        self.debug_day_length = config.get("day_length", None)
        self.stateEntities = []
        self.controlEntities = []
        self.sensorEntities = []
        self.triggerOnDeactivate = []
        self.triggerOnActivate = []
        self.timer_handle = None
        self.block_timer_handle = None
        self.sensor_type = None
        self.night_mode = None
        self.state_attributes_ignore = []
        self.backoff = False
        self.backoff_count = 0
        self.light_params_day = {}
        self.light_params_night = {}
        self.lightParams = {}
        self.name = None
        self.stay = False
        self.start = None
        self.end = None
        self.reset_count = None
        self.transition_behaviours = {}
        # logging.setFormatter(logging.Formatter(FORMAT))
        self.log = logging.getLogger(__name__ + "." + config.get(CONF_NAME))
        self.ignored_event_sources = []
        self.context = None

        self.log.debug(
            "Initialising EntityController entity with this configuration: "
        )
        self.log.debug(
            pprint.pformat(config)
        )
        self.name = config.get(CONF_NAME, "Unnamed Entity Controller")
        self.ignored_event_sources = []

        machine.add_model(
            self
        )  # add here because machine generated methods are being used in methods below.
        self.config_static_strings(config)
        self.config_control_entities(config)
        self.config_state_entities(
            config
        )  # must come after config_control_entities (uses control entities if not set)
        self.config_sensor_entities(config)
        self.config_override_entities(config)
        self.config_transition_behaviours(config)
        self.config_off_entities(config)
        self.config_on_entities(config)
        self.config_normal_mode(config)
        self.config_night_mode(
            config
        )  # must come after normal_mode (uses normal mode parameters if not set)
        self.config_state_attributes_ignore(config)
        self.config_times(config)
        self.config_other(config)
        self.prepare_service_data()

    def update(self, wait=False, **kwargs):
        """ Called from different methods to report a state attribute change """
        # self.log.debug("Update called with {}".format(str(kwargs)))
        for k, v in kwargs.items():
            if v is not None:
                self.entity.set_attr(k, v)

        if wait == False:
            self.entity.do_update()

    def finalize(self):
        self.entity.do_update()

    # =====================================================
    # S T A T E   C H A N G E   C A L L B A C K S
    # =====================================================

    @callback
    def sensor_state_change(self, entity, old, new):
        """ State change callback for sensor entities """
        self.log.debug("sensor_state_change :: %10s Sensor state change to: %s" % ( pprint.pformat(entity), new.state))
        self.log.debug("sensor_state_change :: state: " +  pprint.pformat(self.state))

        try:
            if new.state == old.state:
                self.log.debug("sensor_state_change :: Ignore attribute only change")
                return
        except AttributeError:
            self.log.debug("sensor_state_change :: old NoneType")
            pass

        if self.matches(new.state, self.SENSOR_ON_STATE) and (
            self.is_idle() or self.is_active_timer() or self.is_blocked()
        ):
            self.set_context(new.context)
            self.update(last_triggered_by=entity)
            self.sensor_on()

        if (
            self.matches(new.state, self.SENSOR_OFF_STATE)
            and self.is_duration_sensor()
            and self.is_active_timer()
        ):
            self.set_context(new.context)
            self.update(last_triggered_by=entity, sensor_turned_off_at=datetime.now())

            # If configured, reset timer when duration sensor goes off
            if self.config[CONF_SENSOR_RESETS_TIMER]:
                self.log.debug("sensor_state_change :: CONF_SENSOR_RESETS_TIMER")
                self.update(
                    notes="The sensor turned off and reset the timeout. Timer started."
                )
                self._reset_timer()
            else:
                # We only care about sensor off state changes when the sensor is a duration sensor and we are in active_timer state.
                self.sensor_off_duration()
                self.log.debug("sensor_state_change :: CONF_SENSOR_RESETS_TIMER - normal")

    @callback
    def override_state_change(self, entity, old, new):
        """ State change callback for override entities """
        self.log.debug("override_state_change :: Override state change entity=%s, old=%s, new=%s" % ( entity, old, new))
        if self.matches(new.state, self.OVERRIDE_ON_STATE) and (
            self.is_active()
            or self.is_active_timer()
            or self.is_idle()
            or self.is_blocked()
        ):
            self.set_context(new.context)
            self.update(overridden_by=entity)
            self.override()
            self.update(overridden_at=str(datetime.now()))
        if (
            self.matches(new.state, self.OVERRIDE_OFF_STATE)
            and self.is_override_state_off()
            and self.is_overridden()
        ):
            self.set_context(new.context)
            self.enable()

    @callback
    def state_entity_state_change(self, entity, old, new):
        """ State change callback for state entities. This can be called with either a state change or an attribute change. """
        self.log.debug(
            "state_entity_state_change :: [ Entity: %s, Context: %s ]\n\tOld state: %s\n\tNew State: %s",
            str(entity),
            str(new.context),
            str(old),
            str(new)
        )
        if self.is_ignored_context(new.context):
            self.log.debug("state_entity_state_change :: Ignoring this state change because it came from %s" % (new.context.id))
            return

        #  If the state changed, we definitely want to handle the transition. If only attributes changed, we'll check if the new attributes are significant (i.e., not being ignored).
        try:
            if not old or not new or old == 'off' or new == 'off':
                pass
            else:
                if old.state == new.state:  # Only attributes changed
                    # Build two dictionaries of attributes, excluding the ones we don't want to monitor
                    old_temp = {
                        key: old.attributes[key]
                        for key in old.attributes
                        if key not in self.state_attributes_ignore
                    }
                    new_temp = {
                        key: new.attributes[key]
                        for key in new.attributes
                        if key not in self.state_attributes_ignore
                    }
                    if old_temp == new_temp:
                        self.log.debug("state_entity_state_change :: insignificant attribute change - Ignore the state change altogether")
                        return
                    self.log.debug("state_entity_state_change :: A significant attribute changed and will be handled")
        except AttributeError as a:
            # Most likely one of the states, either new or old, is 'off', so there's no attributes dict attached to the state object.
            self.log.debug(
                "state_entity_state_change :: Most likely one of the states, either new or old, is 'off', so there's no attributes dict attached to the state object: "
                + str(a)
            )
        self.set_context(new.context)
        if self.is_active_timer():
            self.log.debug("state_entity_state_change :: We are in active timer and the state of observed state entities changed.")
            self.control()

        if self.is_blocked() or self.is_active_stay_on(): # if statement required to avoid MachineErrors, cleaner than adding transitions to all possible states.
            self.enable()

    def _start_timer(self):
        self.log.info("_start_timer :: Light params: " + str(self.lightParams))
        if self.backoff_count == 0:
            self.previous_delay = self.lightParams.get(CONF_DELAY, DEFAULT_DELAY)
        else:
            self.log.debug(
                "_start_timer :: Backoff: %s,  count: %s, delay%s, factor: %s",
                self.backoff,
                self.backoff_count,
                self.lightParams.get(CONF_DELAY, DEFAULT_DELAY),
                self.backoff_factor,
            )
            self.previous_delay = round(self.previous_delay * self.backoff_factor, 2)
            if self.previous_delay > self.backoff_max:
                self.log.debug("Max backoff reached. Will not increase further.")
                self.previous_delay = self.backoff_max
            self.update(delay=self.previous_delay)

        expiry_time = datetime.now() + timedelta(seconds=self.previous_delay)

        # not able to use async_call_later because no known way to check whether timer is active.
        # self.timer_handle = event.async_call_later(self.hass, self.previous_delay, self.timer_expire)
        self.timer_handle = Timer(self.previous_delay, self.timer_expire)
        self.timer_handle.start()
        self.update(expires_at=expiry_time)

    def _cancel_timer(self):
        if self.timer_handle.is_alive():
            self.timer_handle.cancel()

    def _reset_timer(self):
        self.log.debug("_reset_timer :: Resetting timer: " + str(self.backoff))
        self._cancel_timer()
        self.update(reset_at=datetime.now())
        if self.backoff:
            self.backoff_count += 1
            self.update(backoff_count=self.backoff_count)
        self._start_timer()

        return True

    def timer_expire(self):
        self.log.debug("timer_expire :: Timer expired")
        if self.is_duration_sensor() and self.is_sensor_on():  # Ignore timer expiry because duration sensor overwrites timer
            self.update(expires_at="pending sensor")
        else:
            self.log.debug("timer_expire :: Trigger timer_expires event")
            self.timer_expires()

    def block_timer_expire(self):
        self.log.debug("block_timer_expire :: Blocked Timer expired")
        self.block_timer_expires()

    # =====================================================
    # S T A T E   M A C H I N E   C O N D I T I O N S
    # =====================================================
    def _override_entity_state(self):
        for e in self.overrideEntities:
            s = self.hass.states.get(e)
            try:
                state = s.state
            except AttributeError as ex:
                self.log.error(
                    "Potential configuration error: Override Entity ({}) does not exist (yet). Please check for spelling and typos. {}".format(
                        e, ex
                    )
                )
                return None

            if self.matches(state, self.OVERRIDE_ON_STATE):
                self.log.debug("Override entities are ON. [%s]", e)
                return e
        self.log.debug("Override entities are OFF.")
        return None

    def is_override_state_off(self):
        return self._override_entity_state() is None

    # def is_within_grace_period(self):
    #     """ Dtermines if the last service call EC made was within the last 2 seconds.
    #     This is important or else EC will react to state changes caused by EC itself which results in going into blocked state."""
    #     return datetime.now() < self.ignore_state_changes_until

    def is_override_state_on(self):
        return self._override_entity_state() is not None

    def _sensor_entity_state(self):
        for e in self.sensorEntities:
            s = self.hass.states.get(e)
            try:
                state = s.state
            except AttributeError as ex:
                self.log.error(
                    "Potential configuration error: Sensor Entity ({}) does not exist (yet). Please check for spelling and typos. {}".format(
                        e, ex
                    )
                )
                return None

            if self.matches(state, self.SENSOR_ON_STATE):
                self.log.debug("Sensor entities are ON. [%s]", e)
                return e
        self.log.debug("Sensor entities are OFF.")
        return None

    def is_sensor_off(self):
        return self._sensor_entity_state() is None

    def is_sensor_on(self):
        return self._sensor_entity_state() is not None

    def _state_entity_state(self):
        for e in self.stateEntities:
            s = self.hass.states.get(e)
            self.log.info(s)
            try:
                state = s.state
            except AttributeError as ex:
                self.log.error(
                    "Potential configuration error: State Entity ({}) does not exist (yet). Please check for spelling and typos. {}".format(
                        e, ex
                    )
                )
                state = 'off'
                return None

            if self.matches(state, self.STATE_ON_STATE):
                self.log.debug("State entities are ON. [%s]", e)
                return e
        self.log.debug("State entities are OFF.")
        return None

    def is_state_entities_off(self):
        return self._state_entity_state() is None

    def is_state_entities_on(self):
        return self._state_entity_state() is not None

    def will_stay_on(self):
        return self.stay

    def is_night(self):
        if self.night_mode is None:
            return False  # if night mode is undefined, it's never night :)
        else:
            self.log.debug("NIGHT MODE ENABLED: " + str(self.night_mode))
            return self.now_is_between(
                self.night_mode[CONF_START_TIME], self.night_mode[CONF_END_TIME]
            )

    def is_event_sensor(self):
        return self.sensor_type == SENSOR_TYPE_EVENT

    def is_duration_sensor(self):
        return self.sensor_type == SENSOR_TYPE_DURATION

    def is_timer_expired(self):
        expired = self.timer_handle.is_alive() == False
        return expired

    def does_sensor_reset_timer(self):
        return self.config[CONF_SENSOR_RESETS_TIMER]

    # =====================================================
    # S T A T E   M A C H I N E   C A L L B A C K S
    # =====================================================
    def on_enter_idle(self):
        self.log.debug("Entering idle")
        # Entering idle due to no events, set a new context with no parent
        self.set_context(None)
        self.do_transition_behaviour(CONF_ON_ENTER_IDLE)
        self.entity.reset_state()

    def on_exit_idle(self):
        self.log.debug("Exiting idle")
        self.do_transition_behaviour(CONF_ON_EXIT_IDLE)

    def on_enter_overridden(self):
        self.log.debug("Entering overridden")
        self.do_transition_behaviour(CONF_ON_ENTER_OVERRIDDEN)

    def on_exit_overridden(self):
        self.log.debug("Exiting overridden")
        self.do_transition_behaviour(CONF_ON_EXIT_OVERRIDDEN)

    def on_enter_active(self):
        self.log.debug("Entering active")
        self.update(last_triggered_at=str(datetime.now()))
        self.backoff_count = 0
        self.prepare_service_data()

        self._start_timer()

        self.log.debug("on_enter_active :: light params before turning on: " + str(self.lightParams))
        self.do_transition_behaviour(CONF_ON_ENTER_ACTIVE)
        self.enter()

    def on_exit_active(self):
        self.log.debug("Exiting active")
        self.log.debug("on_exit_active :: Turning off entities, cancelling timer")
        self._cancel_timer()  # cancel previous timer
        self.update(
            delay=self.lightParams.get(CONF_DELAY)
        )  # no need to update immediately
        self.do_transition_behaviour(CONF_ON_EXIT_ACTIVE)

    def on_enter_blocked(self):
        self.log.debug("Entering blocked")
        self.update(blocked_at=datetime.now())
        self.update(blocked_by=self._state_entity_state())

        self.do_transition_behaviour(CONF_ON_ENTER_BLOCKED)
        if self.block_timeout:
            self.block_timer_handle = Timer(self.block_timeout, self.block_timer_expire)
            self.block_timer_handle.start()
            self.update(block_timeout=self.block_timeout)

    def on_exit_blocked(self):
        self.log.debug("Exiting blocked")
        self.do_transition_behaviour(CONF_ON_EXIT_BLOCKED)
        if self.block_timer_handle and self.block_timer_handle.is_alive():
            self.block_timer_handle.cancel()

    def on_enter_constrained(self):
        self.log.debug("Entering constrained")
        self.do_transition_behaviour(CONF_ON_ENTER_CONSTRAINED)

    def on_exit_constrained(self):
        self.log.debug("Exiting constrained")
        self.do_transition_behaviour(CONF_ON_EXIT_CONSTRAINED)
    # =====================================================
    #    C O N F I G U R A T I O N  &  V A L I D A T I O N
    # =====================================================

    def config_transition_behaviours(self, config):
        self.transition_behaviours = {
            CONF_ON_ENTER_IDLE: CONF_TRANSITION_BEHAVIOUR_OFF,          # By default turn off
            CONF_ON_EXIT_IDLE: CONF_TRANSITION_BEHAVIOUR_IGNORE,
            CONF_ON_ENTER_ACTIVE: CONF_TRANSITION_BEHAVIOUR_ON,         # By default turn on
            CONF_ON_EXIT_ACTIVE: CONF_TRANSITION_BEHAVIOUR_IGNORE,
            CONF_ON_ENTER_OVERRIDDEN: CONF_TRANSITION_BEHAVIOUR_IGNORE,
            CONF_ON_EXIT_OVERRIDDEN: CONF_TRANSITION_BEHAVIOUR_IGNORE,
            CONF_ON_ENTER_CONSTRAINED: CONF_TRANSITION_BEHAVIOUR_IGNORE,
            CONF_ON_EXIT_CONSTRAINED: CONF_TRANSITION_BEHAVIOUR_IGNORE,
            CONF_ON_ENTER_BLOCKED: CONF_TRANSITION_BEHAVIOUR_IGNORE,
            CONF_ON_EXIT_BLOCKED: CONF_TRANSITION_BEHAVIOUR_IGNORE,
        }

        if CONF_BEHAVIOURS in config:
            self.transition_behaviours = {**self.transition_behaviours, **config[CONF_BEHAVIOURS]}

        self.log.debug("config_transition_behaviours :: Transition Behaviours: " +  pprint.pformat(self.transition_behaviours))

    def config_control_entities(self, config):
        self.controlEntities = []

        self.add(self.controlEntities, config, CONF_CONTROL_ENTITY)
        self.add(self.controlEntities, config, CONF_CONTROL_ENTITIES)

        self.log.debug("Control Entities: " +  pprint.pformat(self.controlEntities))

    def config_state_entities(self, config):
        self.stateEntities = []
        self.add(
            self.stateEntities, config, CONF_STATE_ENTITIES
        )  # adding optimistically
        if len(self.stateEntities) > 0:  # now checking whether they actually exist
            self.log.info(
                "State Entities (explicitly defined - I hope you know what you are doing): " + str(self.stateEntities)
            )
            event.async_track_state_change(
                self.hass, self.stateEntities, self.state_entity_state_change
            )

        if len(self.stateEntities) == 0:
            # If no state entities are defined, use control entites as state
            self.stateEntities = self.controlEntities.copy()
            self.log.debug(
                "Added Control Entities as state entities (default): " + str(self.stateEntities)
            )
            event.async_track_state_change(
                self.hass, self.stateEntities, self.state_entity_state_change
            )

    def config_off_entities(self, config):

        self.triggerOnDeactivate = []
        self.add(self.triggerOnDeactivate, config, CONF_TRIGGER_ON_DEACTIVATE)
        if len(self.triggerOnDeactivate) > 0:
            self.log.info("Off Entities: " +  pprint.pformat(self.triggerOnDeactivate))

    def config_on_entities(self, config):
        self.triggerOnActivate = []
        self.add(self.triggerOnActivate, config, CONF_TRIGGER_ON_ACTIVATE)
        if len(self.triggerOnActivate) > 0:
            self.log.info("On Entities: " +  pprint.pformat(self.triggerOnActivate))

    def config_sensor_entities(self, config):
        self.sensorEntities = []
        self.add(self.sensorEntities, config, CONF_SENSOR)
        self.add(self.sensorEntities, config, CONF_SENSORS)

        if len(self.sensorEntities) == 0:
            self.log.error(
                "No sensor entities defined. You must define at least one sensor entity."
            )

        self.log.debug("Sensor Entities: " +  pprint.pformat(self.sensorEntities))

        event.async_track_state_change(
            self.hass, self.sensorEntities, self.sensor_state_change
        )

    def config_static_strings(self, config):
        DEFAULT_ON = ["on", "playing", "home", "True"]
        DEFAULT_OFF = ["off", "idle", "paused", "away", "False"]
        self.CONTROL_ON_STATE = config.get("control_states_on", DEFAULT_ON)
        self.CONTROL_OFF_STATE = config.get("control_states_off", DEFAULT_OFF)
        self.SENSOR_ON_STATE = config.get("sensor_states_on", DEFAULT_ON)
        self.SENSOR_OFF_STATE = config.get("sensor_states_off", DEFAULT_OFF)
        self.OVERRIDE_ON_STATE = config.get("override_states_on", DEFAULT_ON)
        self.OVERRIDE_OFF_STATE = config.get("override_states_off", DEFAULT_OFF)
        self.STATE_ON_STATE = config.get("state_states_on", DEFAULT_ON)
        self.STATE_OFF_STATE = config.get("state_states_off", DEFAULT_OFF)

        on = config.get("state_strings_on", False)
        if on:
            self.CONTROL_ON_STATE.extend(on)
            self.CONTROL_ON_STATE.extend(on)
            self.SENSOR_ON_STATE.extend(on)
            self.OVERRIDE_ON_STATE.extend(on)
            self.STATE_ON_STATE.extend(on)

        off = config.get("state_strings_off", False)
        if off:
            self.CONTROL_OFF_STATE.extend(off)
            self.SENSOR_OFF_STATE.extend(off)
            self.OVERRIDE_OFF_STATE.extend(off)
            self.STATE_OFF_STATE.extend(off)

    def config_night_mode(self, config):
        """
            Configured night mode parameters. If no night_mode service
            parameters are given, the day mode parameters are used instead.
            If those do not exist, the
        """
        if "night_mode" in config:
            self.night_mode = config[CONF_NIGHT_MODE]
            night_mode = config[CONF_NIGHT_MODE]
            self.light_params_night[CONF_DELAY] = night_mode.get(
                CONF_DELAY, config.get(CONF_DELAY, DEFAULT_DELAY)
            )
            self.light_params_night[CONF_SERVICE_DATA] = night_mode.get(
                CONF_SERVICE_DATA, self.light_params_day.get(CONF_SERVICE_DATA)
            )
            self.light_params_night[CONF_SERVICE_DATA_OFF] = night_mode.get(
                CONF_SERVICE_DATA_OFF, self.light_params_day.get(CONF_SERVICE_DATA_OFF)
            )

            if not "start_time" in night_mode:
                self.log.error("Night mode requires a start_time parameter !")

            if not "end_time" in night_mode:
                self.log.error("Night mode requires a end_time parameter !")

    def config_state_attributes_ignore(self, config):
        self.add(self.ignored_event_sources, config, CONF_IGNORED_EVENT_SOURCES)
        self.add(self.state_attributes_ignore, config, CONF_STATE_ATTRIBUTES_IGNORE)
        self.log.debug(
            "Ignoring events (state changes) caused by the following entities): %s",
            self.ignored_event_sources,
        )
        self.log.debug(
            "Ignoring state changes on the following attributes: %s",
            self.state_attributes_ignore,
        )

    def config_normal_mode(self, config):
        self.log.info("Service data set up")
        params = {}
        params[CONF_DELAY] = config.get(CONF_DELAY, DEFAULT_DELAY)
        params[CONF_SERVICE_DATA] = config.get(CONF_SERVICE_DATA, None)
        params[CONF_SERVICE_DATA_OFF] = config.get(CONF_SERVICE_DATA_OFF, None)
        self.light_params_day = params

    @property
    def start_time(self):
        """ Wrapper for _start_time_private """
        return self.debug_time_wrapper(self._start_time_private)

    @property
    def end_time(self):
        """ Wrapper for _end_time_private """
        return self.debug_time_wrapper(self._end_time_private)

    def config_times(self, config):
        self._start_time_private = None
        self._end_time_private = None
        if CONF_START_TIME in config and CONF_END_TIME in config:
            # FOR OPTIONAL DEBUGGING: for initial setup use the raw input value
            self._start_time_private = config.get(CONF_START_TIME)
            self._end_time_private = config.get(CONF_END_TIME)
            start_time_parsed = self.parse_time(self.start_time)
            self.log.debug("start_time_parsed: %s", start_time_parsed)

            self.log.debug("futurize outputs %s", self.futurize(start_time_parsed))

            parsed_start = self.parse_time(self.start_time, aware=False)
            parsed_end = self.parse_time(self.end_time, aware=False)
            # parsed_start = datetime.now() + timedelta(seconds=5)
            # parsed_end = datetime.now() + timedelta(seconds=10)
            # FOR OPTIONAL DEBUGGING: subsequently use normal delay
            sparts = re.search("^(now\s*[+-]\s*\d+)", config.get(CONF_START_TIME))
            if sparts is not None:
                self._start_time_private = sparts.group(1)
            eparts = re.search("^(now\s*[+-]\s*\d+)", config.get(CONF_END_TIME))
            if eparts is not None:
                self._end_time_private = eparts.group(1)

            self.update(start=self.start_time)
            self.update(end=self.end_time)

            parsed_start = self.futurize(parsed_start)
            parsed_end = self.futurize(parsed_end)
            self.log.debug("Setting FIRST START callback for %s", parsed_start)
            self.log.debug("Setting FIRST END callback for %s", parsed_end)

            self.start_time_event_hook = event.async_track_point_in_time(
                self.hass, self.start_time_callback, parsed_start
            )
            self.end_time_event_hook = event.async_track_point_in_time(
                self.hass, self.end_time_callback, parsed_end
            )

            if not self.now_is_between(self.start_time, self.end_time):
                self.log.debug(
                    "Constrain period active. Scheduling transition to 'constrained'"
                )
                event.async_call_later(self.hass, 1, self.constrain_entity)

        self.log_config()




    def config_override_entities(self, config):
        self.overrideEntities = []
        self.add(self.overrideEntities, config, "override")
        self.add(self.overrideEntities, config, "overrides")

        if len(self.overrideEntities) > 0:
            self.log.debug("Override Entities: " +  pprint.pformat(self.overrideEntities))
            event.async_track_state_change(
                self.hass, self.overrideEntities, self.override_state_change
            )

    def config_other(self, config):
        self.do_draw = config.get("draw", False)
        self.ignore_state_changes_until = datetime.now()
        self.homeassistant_turn_on_domains = ['group'] # domains that do not have their own turn_on service and rely on homeassistant.turn_on

        self.config[CONF_SENSOR_RESETS_TIMER] = config.get(CONF_SENSOR_RESETS_TIMER)

        self.block_timeout = config.get(CONF_BLOCK_TIMEOUT, None)
        self.image_prefix = config.get("image_prefix", "/fsm_diagram_")
        self.image_path = config.get("image_path", "/conf/temp")
        self.backoff = config.get("backoff", False)
        self.stay = config.get("stay_mode", False)

        if self.backoff:
            self.log.debug("config_other :: setting up backoff. Using delay as initial backoff value.")
            self.backoff_factor = config.get("backoff_factor", 1.1)
            self.backoff_max = config.get("backoff_max", 300)

        if config.get(CONF_SENSOR_TYPE_DURATION):
            self.sensor_type = SENSOR_TYPE_DURATION
        else:
            self.sensor_type = SENSOR_TYPE_EVENT

        if CONF_SENSOR_TYPE in config:
            self.sensor_type = config.get(CONF_SENSOR_TYPE)

        self.update(sensor_type=self.sensor_type)

    # =====================================================
    #    E V E N T   C A L L B A C K S
    # =====================================================

    @callback
    def constrain_entity(self, evt):
        """
            Event callback used on component setup if current time requires entity to start in constrained state.
        """
        self.constrain()

    @callback
    def end_time_callback(self, evt):
        """
            Called when `end_time` is reached, will change state to `constrained` and schedule `start_time` callback.
        """
        self.log.debug("end_time_callback :: Triggered")
        # must be reparsed to get up to date sunset/sunrise times
        x = self.parse_time(self.end_time)

        parsed_end = self.futurize(x)
        self.log.debug("end_time_callback :: New callback set to %s (future)", parsed_end)
        self.end_time_event_hook = event.async_track_point_in_time(
            self.hass, self.end_time_callback, parsed_end
        )
        self.update(end_time=parsed_end)

        # must be down here to make sure new callback is set regardless of exceptions
        self.do_transition_behaviour(CONF_ON_ENTER_CONSTRAINED)
        self.constrain()

    @callback
    def start_time_callback(self, evt):
        """
            Called when `start_time` is reached, will change state to `idle` and schedule `end_time` callback.
        """
        self.log.debug("start_time_callback :: Triggered")
        # must be reparsed to get up to date sunset/sunrise times
        # if self.debug_day_length:
        #     x = self.make_naive(dt.now() + timedelta(seconds=int(self.debug_day_length)))
        #     self.log.debug("using debug day lengh %s", x)
        # else:
        x = self.parse_time(self.start_time)

        parsed_start = self.futurize(x)
        self.log.debug(
            "start_time_callback :: New callback set to %s (future)" % parsed_start
        )
        self.start_time_event_hook = event.async_track_point_in_time(
            self.hass, self.start_time_callback, parsed_start
        )

        self.update(start_time=parsed_start)

        if self.is_state_entities_on():
            self.blocked()
        else:
            self.enable()
        self.do_transition_behaviour(CONF_ON_EXIT_CONSTRAINED)

    # =====================================================
    #    H E L P E R   F U N C T I O N S        ( N E W )
    # =====================================================

    def handleTriggerOnDeactivateEntities(self):
        """ Entities that are defined outside of control entities via the `triggerOnDetivate` key. """
        if len(self.triggerOnDeactivate) > 0:
            self.log.info("handleTriggerOnDeactivateEntities :: Triggering Deactivation entities (Yes! params passed along)")
            for e in self.triggerOnDeactivate:
                self.log.debug("Triggering with turn_on call: %s", e)
                if self.lightParams.get(CONF_SERVICE_DATA_OFF) is not None:
                    self.log.debug(
                        "Triggering with turn_on call %s with service parameters %s",
                        e,
                        self.lightParams.get(CONF_SERVICE_DATA_OFF),
                    )
                    self.call_service(e, "turn_on", **self.lightParams.get(CONF_SERVICE_DATA_OFF))
                else:
                    self.log.debug("Triggering with turn_on call %s (no parameters provided to pass to service call)", e)
                    self.call_service(e, "turn_on")

    def handleTriggerOnActivateEntities(self):
        """ Entities that are defined outside of control entities via the `triggerOnActivate` key. """
        if len(self.triggerOnActivate) > 0:
            self.log.info("handleTriggerOnActivateEntities :: Triggering Activation entities (Yes! params passed along)")
            for e in self.triggerOnActivate:
                # if light params are defined
                if self.lightParams.get(CONF_SERVICE_DATA) is not None:
                    self.log.debug(
                        "Triggering with turn_on call %s with service parameters %s",
                        e,
                        self.lightParams.get(CONF_SERVICE_DATA),
                    )
                    self.call_service(
                        e, "turn_on", **self.lightParams.get(CONF_SERVICE_DATA)
                    )
                else:
                    self.log.debug("Turning on %s (no parameters provided to pass to service call)", e)
                    self.call_service(e, "turn_on")

    def turn_on_control_entities(self):
        self.handleTriggerOnActivateEntities()

        for e in self.controlEntities:
            # if light params are defined
            if self.lightParams.get(CONF_SERVICE_DATA) is not None:
                self.log.debug(
                    "turn_on_control_entities :: Turning on %s with service parameters %s",
                    e,
                    self.lightParams.get(CONF_SERVICE_DATA),
                )
                self.call_service(
                    e, "turn_on", **self.lightParams.get(CONF_SERVICE_DATA)
                )
            else:
                self.log.debug(
                    "turn_on_control_entities :: Turning on %s (no parameters passed to service call)", e
                )
                self.call_service(e, "turn_on")

    def turn_off_control_entities(self):
        self.handleTriggerOnDeactivateEntities()
        for e in self.controlEntities:
            self.log.debug("turn_off_control_entities :: Turning off %s", e)

            if self.lightParams.get(CONF_SERVICE_DATA_OFF) is not None:
                self.call_service(
                    e, "turn_off", **self.lightParams.get(CONF_SERVICE_DATA_OFF)
                )
            else:
                self.call_service(e, "turn_off")

    def now_is_between(self, start_time_str, end_time_str, name=None):
        start_time = (self._parse_time(start_time_str, name))["datetime"]
        end_time = (self._parse_time(end_time_str, name))["datetime"]
        now = dt.as_local(dt.now())
        start_date = now.replace(
            hour=start_time.hour, minute=start_time.minute, second=start_time.second
        )
        end_date = now.replace(
            hour=end_time.hour, minute=end_time.minute, second=end_time.second
        )
        if end_date < start_date:
            # Spans midnight
            if now < start_date and now < end_date:
                now = now + timedelta(days=1)
            end_date = end_date + timedelta(days=1)

        self.log.debug("now_is_between start time %s", start_date)
        self.log.debug("now_is_between end time %s", end_date)
        return start_date <= now <= end_date

    def parse_time(self, time_str, name=None, aware=False):
        if aware is True:
            return dt.as_local(self._parse_time(time_str, name)["datetime"]).time()
        else:
            return self.make_naive(
                (self._parse_time(time_str, name))["datetime"]
            ).time()

    def parse_datetime(self, time_str, name=None, aware=False):
        if aware is True:
            return dt.as_local(self._parse_time(time_str, name)["datetime"])
        else:
            return self.make_naive(
                dt.as_local(self._parse_time(time_str, name)["datetime"])
            )

    def _parse_time(self, time_str, name=None):
        parsed_time = None
        sun = None
        offset = 0
        parts = re.search("^(\d+)-(\d+)-(\d+)\s+(\d+):(\d+):(\d+)$", str(time_str))
        if parts:
            this_time = datetime(
                int(parts.group(1)),
                int(parts.group(2)),
                int(parts.group(3)),
                int(parts.group(4)),
                int(parts.group(5)),
                int(parts.group(6)),
                0,
            )
            parsed_time = dt.as_local(this_time)
        else:
            parts = re.search("^(\d+):(\d+):(\d+)$", str(time_str))
            if parts:
                today = dt.as_local(dt.now())
                time_temp = time(
                    int(parts.group(1)), int(parts.group(2)), int(parts.group(3)), 0
                )
                parsed_time = today.replace(
                    hour=time_temp.hour,
                    minute=time_temp.minute,
                    second=time_temp.second,
                    microsecond=0,
                )

            else:
                if time_str == "sunrise":
                    parsed_time = self.sunrise(True)
                    sun = "sunrise"
                    offset = 0
                elif time_str == "sunset":
                    parsed_time = self.sunset(True)
                    sun = "sunset"
                    offset = 0
                else:
                    parts = re.search(
                        "^sunrise\s*([+-])\s*(\d+):(\d+):(\d+)$", str(time_str)
                    )
                    if parts:

                        sun = "sunrise"
                        if parts.group(1) == "+":
                            td = timedelta(
                                hours=int(parts.group(2)),
                                minutes=int(parts.group(3)),
                                seconds=int(parts.group(4)),
                            )
                            offset = td.total_seconds()
                            parsed_time = self.sunrise(True) + td
                        else:
                            td = timedelta(
                                hours=int(parts.group(2)),
                                minutes=int(parts.group(3)),
                                seconds=int(parts.group(4)),
                            )
                            offset = td.total_seconds() * -1
                            parsed_time = self.sunrise(True) - td
                    else:
                        parts = re.search(
                            "^sunset\s*([+-])\s*(\d+):(\d+):(\d+)$", str(time_str)
                        )
                        if parts:
                            sun = "sunset"
                            if parts.group(1) == "+":
                                td = timedelta(
                                    hours=int(parts.group(2)),
                                    minutes=int(parts.group(3)),
                                    seconds=int(parts.group(4)),
                                )
                                offset = td.total_seconds()
                                parsed_time = self.sunset(True) + td
                            else:
                                td = timedelta(
                                    hours=int(parts.group(2)),
                                    minutes=int(parts.group(3)),
                                    seconds=int(parts.group(4)),
                                )
                                offset = td.total_seconds() * -1
                                parsed_time = self.sunset(True) - td
        if parsed_time is None:
            if name is not None:
                raise ValueError("%s: invalid time string: %s", name, time_str)
            else:
                raise ValueError("invalid time string: %s", time_str)
        # self.log.debug("Result of parsing: %s",
        #                {"datetime": parsed_time, "sun": sun, "offset": offset})
        return {"datetime": parsed_time, "sun": sun, "offset": offset}

    def make_naive(self, dts):
        local = dt.as_local(dts)
        return datetime(
            local.year,
            local.month,
            local.day,
            local.hour,
            local.minute,
            local.second,
            local.microsecond,
        )

    def sunset(self, aware):
        t = get_astral_event_date(
            self.hass, SUN_EVENT_SUNSET, datetime.now().replace(hour=0)
        )
        if aware is True:
            return dt.as_local(t)
        else:
            return t

    def sunrise(self, aware):
        t = get_astral_event_date(
            self.hass, SUN_EVENT_SUNRISE, datetime.now().replace(hour=0)
        )
        if aware is True:
            return dt.as_local(t)
        else:
            return t

    def next_sunrise(self, offset=0):
        mod = offset
        while True:

            next_rising_dt = self.sunrise(True) + timedelta(mod)
            if next_rising_dt > dt.now():
                break

            mod += 1

        return next_rising_dt

    def next_sunset(self, offset=0):
        mod = offset
        while True:

            next_setting_dt = self.sunset(True) + timedelta(mod)
            if next_setting_dt > dt.now():
                break

            mod += 1

        return next_setting_dt

    # =====================================================
    #    H E L P E R   F U N C T I O N S    ( C U S T O M )
    # =====================================================

    # def adjust_times(self, start, end):
    #     """ Makes sure that a time period is in the future. """
    #     self.log.debug("Parsed start time (unadjusted) %s", start)
    #     self.log.debug("Parsed end time (unadjusted) %s", end)
    #
    #     # set start_time callback: if time passed, use tomorrow
    #     # --------s--------n----|12am|--s(new)--------
    #     #         \_________>>>________/
    #     now = datetime.now()
    #     if start <= now:
    #         start += timedelta(1)  # start time is tomorrow!
    #
    #     # we now need parsed_end to come after the new parse_start
    #     # (1) ---s---e---now
    #     # (2) ---e---s---now
    #     if end <= now:
    #         end += timedelta(1)  # (1)
    #     # if end <= start:
    #     # bump again because its still before s
    #     #    end += timedelta(1)  # (2)
    #     return start, end

    def prepare_service_data(self):
        """
            Called when entering active state and on initial set up to set
            correct service parameters.
        """
        if self.is_night():
            self.log.debug(
                "Using NIGHT MODE parameters: " + str(self.light_params_night)
            )
            self.lightParams = self.light_params_night
            self.update(mode=MODE_NIGHT)
        else:
            self.log.debug("Using DAY MODE parameters: " + str(self.light_params_day))
            self.lightParams = self.light_params_day
            if self.night_mode is not None:
                self.update(mode=MODE_DAY)  # only show when night mode set up
        self.update(delay=self.lightParams.get(CONF_DELAY))

    def call_service(self, entity, service, **service_data):
        """ Helper for calling HA services with the correct parameters """
        self.log.debug("call_service :: Calling service " + service + " on " + entity)
        # self.ignore_state_changes_until = datetime.now() + timedelta(seconds=self.config.get(CONF_IGNORE_STATE_CHANGES_UNTIL, 2))
        # self.log.debug("call_service :: Setting ignore_state_changes_until to " + str(self.ignore_state_changes_until))

        domain, e = entity.split(".")
        if service in ['turn_on','turn_off'] and domain in self.homeassistant_turn_on_domains:
            domain = "homeassistant"
            self.log.debug("call_service :: Actually calling service %s on %s via the %s domain because the entity domain requires it." % (service, entity, domain))
        params = {}
        if service_data is not None:
            params = service_data

        params["entity_id"] = entity
        self.hass.async_create_task(
            self.hass.services.async_call(domain, service, service_data, context=self.context)
        )
        self.update(service_data=service_data)

    def set_context(self, parent: Optional[Context] = None) -> None:
        """Set the context used when calling other services.

        The new ID is linked to the context (`parent`) of the triggering event
        and will be unique per trigger.
        """
        # Unique name per EC instance, but short enough to fit within id length
        name_hash = hashlib.sha1(self.name.encode("UTF-8")).hexdigest()[:6]
        unique_id = uuid_util.random_uuid_hex()
        context_id = f"{DOMAIN_SHORT}_{name_hash}_{unique_id}"
        # Restrict id length to database field size
        context_id = context_id[:CONTEXT_ID_CHARACTER_LIMIT]
        # parent_id only exists for a non-None parent
        parent_id = parent.id if parent else None
        self.context = Context(parent_id=parent_id, id=context_id)
        # Set the EC entity's context so the logbook can identify the source of
        # events that will be generated by this object.
        self.entity.async_set_context(self.context)

    def is_ignored_context(self, context: Context) -> bool:
        """Should the event with the given `context` be ignored?"""
        if any(re.match(pattern + r"\b", context.id) is not None
               for pattern in self.ignored_event_sources):
            # Matched an ignore_event_source regex pattern
            return True
        if context.id.startswith(f"{DOMAIN_SHORT}_"):
            # This is an EC-generated event
            return True
        return False

    def matches(self, value, list):
        """
            Checks whether a string is contained in a list (used for matching state strings)
        """
        try:
            index = list.index(value)
            return True
        except ValueError:
            return False

    def five_seconds_from_now(self, sun):
        """ Returns a timedelta that will result in a sunrise trigger in 5 seconds time"""

        return (
            dt.now()
            + timedelta(seconds=5)
            - get_astral_event_date(self.hass, sun, datetime.now())
        )

    def five_minutes_ago(self, sun):
        """ Returns a timedelta that will result in a sunrise trigger in 5 seconds time"""
        return (
            dt.now()
            - timedelta(minutes=5)
            - get_astral_event_date(self.hass, sun, datetime.now())
        )

    def add(self, list, config, key=None):
        """ Adds e (which can be a string or list or config or Template) to the list
            if e is defined.
            If its a template, we have to create the Template object and register state listeners
            self.add(self.controlEntities, config, CONF_CONTROL_ENTITIES)

        """
        if config is not None:
            v = []
            if key is not None:
                if key in config:  # must be in separate if statement
                    v = config[key]
            else:
                v = config
            if type(v) == str:

                list.append(v)
            else:
                list.extend(v)
        else:
            self.log.debug("Tried to configure %s but supplied config was None" % (key))
        return len(v) > 0

    def futurize(self, timet):
        """ Returns tomorrows time if time is in the past.
            Input time should be offset aware
         """

        # self.log.debug("-------------------- futurize ------------------------")
        # self.log.debug("Input (naive) %s ", timet)
        today = date.today()
        try:
            t = datetime.combine(today, timet)
        except TypeError as e:
            t = timet
        x = datetime.now()
        # self.log.debug("input time: " + str(t))

        # self.log.debug("current time: " + str(x))
        while t <= x:
            if t <= x:
                if self.debug_day_length is not None:
                    t = t + timedelta(seconds=int(self.debug_day_length))  # tomorrow!
                else:
                    t = t + timedelta(1)  # tomorrow!
                # self.log.debug( "Time already happened. Returning tomorrow instead. " + str(t))
            else:
                self.log.debug("Time still happening today. " + str(t))
        # self.log.debug("output time: %s", t)
        # self.log.debug("-------------------- futurize (END) -------------------")
        return t

    def debug_time_wrapper(self, timet):
        """

            Injects some debugging capability. Number is parenthesis is the
            first delay used on initial component setup. (This creates a time
            difference between start and end time callbacks.)

            The other number after the + sign is the standard period.
            In real life, this would be 24 hours, for debugging you can make
            it a few seconds to see the app change from idle to constrained.

            start_time: now + 5 (3)
            end_time: now + 5 (6)

            This function is used to wrap CONF_START_TIME and CONF_END_TIME
            and should only be called by the corresponding class properties!

            See config_times.
        """
        s = timet
        parts = re.search("^now\s*([+-])\s*(\d+)\s*\(?(\d+)?\)?$", timet)
        if parts:
            sign = parts.group(1)
            first_delay = parts.group(3)
            delay = parts.group(2)
            now = dt.now()
            self.log.debug("now %s", now)
            delta = timedelta(seconds=int(delay))
            if first_delay is not None:
                delta = timedelta(seconds=int(first_delay))
            if sign == "-":
                now = now - delta
            else:
                now = now + delta

            # self.log.debug("now + delta %s", now)

            s = str(self.make_naive(now).time().replace(microsecond=0))

        # self.log.debug("config time s %s", s)
        return s

    def log_config(self):
        self.log.debug("--------------------------------------------------")
        self.log.debug("       C O N F I G U R A T I O N   D U M P        ")
        self.log.debug("--------------------------------------------------")
        self.log.debug("Entity Controller       %s", self.name)
        self.log.debug("Sensor Entities         %s", str(self.sensorEntities))
        self.log.debug("Control Entities:       %s", str(self.controlEntities))
        self.log.debug("State Entities:         %s", str(self.stateEntities))
        self.log.debug("Activate Trigger E.:    %s", str(self.triggerOnActivate))
        self.log.debug("Deactivate Trigger E.:  %s", str(self.triggerOnDeactivate))
        self.log.debug("Ignored state attrs:    %s", str(self.state_attributes_ignore))
        self.log.debug("Light params:           %s", str(self.lightParams))
        self.log.debug("        -------        Time        -------        ")
        self.log.debug("Start time:             %s", self._start_time_private)
        self.log.debug("End time:               %s", self._end_time_private)
        self.log.debug("DT Now:                 %s", dt.now())
        self.log.debug("datetime Now:           %s", datetime.now())
        self.log.debug("Next Sunrise:           %s", self.next_sunrise(True))
        self.log.debug("Next Sunset:            %s", self.next_sunset(True))
        self.log.debug("        -------        Sun         -------        ")
        self.log.debug("Sunrise:                %s", self.sunrise(True))
        self.log.debug("Sunset:                 %s", self.sunset(True))
        self.log.debug("Sunset Diff (to now): %s", self.next_sunset() - dt.now())
        self.log.debug("Sunrise Diff(to now): %s", self.next_sunset() - dt.now())
        self.log.debug("Transition Behaviours: %s",  str(self.transition_behaviours))
        self.log.debug("--------------------------------------------------")

    def store_transition_behaviour(self, key, behaviour):
        """ manages transition_behaviour map """
        self.transition_behaviours[key] = behaviour

    def get_transition_behaviour(self, key):
        """ manages transition_behaviour map """
        if key in self.transition_behaviours:
            return self.transition_behaviours[key]
        else:
            return None

    def do_transition_behaviour(self, behaviour):
        """ Wrapper method for acting on transition behaviours such as at time of end constraint of state transitions from override state. """
        self.log.debug("%10s | Performing Transition Behaviour" % (behaviour))
        action = self.get_transition_behaviour(behaviour)
        if action:
            self.log.debug("%10s | Action - %s" % (behaviour, action))
            if action == CONF_TRANSITION_BEHAVIOUR_ON:
                self.log.debug("%10s | Performing Action - Turning on" % (behaviour))
                self.turn_on_control_entities()
            if action == CONF_TRANSITION_BEHAVIOUR_OFF:
                self.log.debug("%10s | Performing Action - Turning off" % (behaviour))
                self.turn_off_control_entities()
