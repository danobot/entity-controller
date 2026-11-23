"""Download the current runtime state and recent controller transitions."""

from .const import CONF_ENABLED, SUBENTRY_CONTROLLER


async def async_get_config_entry_diagnostics(hass, entry):
    """Return per-controller diagnostics without entity IDs or service parameters."""
    runtime = getattr(entry, "runtime_data", None)
    diagnostics = {}
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_CONTROLLER:
            continue
        controller = runtime.controllers.get(subentry_id) if runtime and runtime.active else None
        diagnostics[subentry_id] = {
            "enabled": subentry.data.get(CONF_ENABLED, True),
            "state": controller.state if controller else None,
            "timer_expires_at": controller.attributes.get("expires_at") if controller else None,
            "transitions": list(controller.transitions) if controller else [],
        }
    return {"controllers": diagnostics}
