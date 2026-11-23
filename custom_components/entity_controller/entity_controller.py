"""Manage controller entities independently within the shared config entry."""

from asyncio import Lock

from homeassistant.helpers import entity_platform, entity_registry

from . import EntityController, create_machine
from .config import controller_config
from .const import CONF_ENABLED, CONF_IMPORTED_FROM_YAML, SUBENTRY_CONTROLLER


async def async_setup_entry(hass, entry, async_add_entities):
    """Keep the original entity domain and link each entity to its subentry."""
    runtime = entry.runtime_data = ControllerRuntime(entity_platform.async_get_current_platform())
    entry.async_on_unload(entry.add_update_listener(runtime.async_sync))
    await runtime.async_sync(hass, entry)


class ControllerRuntime:
    """Apply subentry changes to the affected controllers only."""

    def __init__(self, platform):
        self.platform = platform
        self.lock = Lock()
        self.active = True
        self.controllers = {}
        self._saved_data = {}

    async def async_sync(self, hass, entry):
        async with self.lock:
            if not self.active:
                return

            enabled = {
                subentry_id: subentry for subentry_id, subentry in entry.subentries.items()
                if subentry.subentry_type == SUBENTRY_CONTROLLER
                and subentry.data.get(CONF_ENABLED, True)
            }
            for subentry_id in self.controllers.keys() - enabled.keys():
                controller = self.controllers.pop(subentry_id)
                self._saved_data.pop(subentry_id)
                if controller.may_update:
                    await controller.async_remove()

            for subentry_id, subentry in enabled.items():
                if subentry_id not in entry.subentries or not subentry.data.get(CONF_ENABLED, True):
                    continue
                saved_data = subentry.data
                controller = self.controllers.get(subentry_id)
                if controller is None:
                    controller = EntityController(
                        hass,
                        controller_config(subentry),
                        create_machine(),
                        name=subentry.title,
                        imported=subentry.data.get(CONF_IMPORTED_FROM_YAML, False),
                    )
                    await self.platform.async_add_entities(
                        [controller], config_subentry_id=subentry_id
                    )
                    self.controllers[subentry_id] = controller
                elif controller.may_update:
                    self._update_controller(hass, controller, subentry)
                self._saved_data[subentry_id] = saved_data

    def _update_controller(self, hass, controller, subentry):
        if controller.name != subentry.title:
            controller.friendly_name = subentry.title
            registry = entity_registry.async_get(hass)
            registry.async_update_entity(controller.entity_id, original_name=subentry.title)
            controller.do_update()
        if self._saved_data[subentry.subentry_id] is not subentry.data:
            controller.apply_options(controller_config(subentry))
