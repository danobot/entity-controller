"""Import YAML controllers and consolidate legacy config entries."""

import json
import logging
from types import MappingProxyType

from homeassistant.config_entries import SOURCE_IMPORT, ConfigSubentry
from homeassistant.helpers import entity_registry as er
import voluptuous as vol

from .config import normalize_yaml
from .const import (
    CONF_ENABLED,
    CONF_IMPORTED_FROM_YAML,
    DOMAIN,
    INTEGRATION_UNIQUE_ID,
    SUBENTRY_CONTROLLER,
)

_LOGGER = logging.getLogger(__name__)


async def async_import_controllers(hass, yaml_config):
    """Merge existing controllers into the shared entry, retaining saved edits."""
    manager = hass.config_entries
    async with hass.data[DOMAIN]["import_lock"]:
        legacy_entries = [
            entry for entry in manager.async_entries(DOMAIN)
            if entry.version == 1 and entry.unique_id not in (None, INTEGRATION_UNIQUE_ID)
        ]
        yaml_controllers = {}
        for slug, settings in (yaml_config.get(DOMAIN) or {}).items():
            try:
                config = normalize_yaml(settings)
                json.dumps(config, allow_nan=False)
            except (vol.Invalid, TypeError, ValueError) as err:
                _LOGGER.error("Cannot import Entity Controller %s: %s", slug, err)
                continue
            yaml_controllers[slug] = config

        if not legacy_entries and not yaml_controllers:
            return

        parent = manager.async_entry_for_domain_unique_id(DOMAIN, INTEGRATION_UNIQUE_ID)
        if parent is None:
            await manager.flow.async_init(DOMAIN, context={"source": SOURCE_IMPORT})
            parent = manager.async_entry_for_domain_unique_id(DOMAIN, INTEGRATION_UNIQUE_ID)
            if parent is None:
                return

        subentries = {subentry.unique_id: subentry for subentry in parent.subentries.values()}
        registry = er.async_get(hass)
        for legacy in legacy_entries:
            slug = legacy.unique_id
            if slug not in subentries:
                data = {**legacy.data, **legacy.options}
                data.pop("friendly_name", None)
                data[CONF_ENABLED] = not legacy.disabled_by
                data[CONF_IMPORTED_FROM_YAML] = legacy.source == SOURCE_IMPORT
                subentries[slug] = _add_controller(manager, parent, slug, legacy.title, data)

            _reassign_entity(registry, parent, subentries[slug])
            await manager.async_remove(legacy.entry_id)

        for slug, data in yaml_controllers.items():
            if slug in subentries:
                continue
            title = data.pop("friendly_name", None) or slug
            data[CONF_IMPORTED_FROM_YAML] = True
            subentry = _add_controller(manager, parent, slug, title, data)
            _reassign_entity(registry, parent, subentry)


def _add_controller(manager, parent, slug, title, data):
    subentry = ConfigSubentry(
        subentry_type=SUBENTRY_CONTROLLER,
        unique_id=slug,
        title=title,
        data=MappingProxyType(data),
    )
    manager.async_add_subentry(parent, subentry)
    return subentry


def _reassign_entity(registry, parent, subentry):
    entity_id = registry.async_get_entity_id(DOMAIN, DOMAIN, subentry.unique_id)
    if entity_id is None:
        return
    original = registry.async_get(entity_id)
    changes = {"config_entry_id": parent.entry_id, "config_subentry_id": subentry.subentry_id}
    if original.disabled_by == er.RegistryEntryDisabler.CONFIG_ENTRY:
        changes["disabled_by"] = None
    registry.async_update_entity(entity_id, **changes)
