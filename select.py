"""Select platform for Daikin VAM-FC9 ventilation mode.

Exposes a SelectEntity with options (auto/erv/bypass) to control the
ventilation operating mode of VAM-FC9 recuperation units.  Only created
when the device is detected as a ventilation unit during startup probe.

The ventilation mode is read via CMD 0x0031 and set via CMD 0x4031
(param 0x20).
"""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MadokaCoordinator
from .madoka_protocol import VentilationMode, VentilationRate

_LOGGER = logging.getLogger(__name__)

MODE_TO_OPTION = {
    VentilationMode.AUTO: "auto",
    VentilationMode.ERV: "erv",
    VentilationMode.BYPASS: "bypass",
}

OPTION_TO_MODE = {v: k for k, v in MODE_TO_OPTION.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Daikin ventilation mode select from a config entry."""
    coordinator: MadokaCoordinator = hass.data[DOMAIN][entry.entry_id]
    if not coordinator.state.is_ventilation_device:
        return
    async_add_entities([DaikinMadokaVentilationMode(coordinator)])


class DaikinMadokaVentilationMode(
    CoordinatorEntity[MadokaCoordinator], SelectEntity
):
    """Select entity for ventilation mode (AUTO/ERV/BYPASS)."""

    _attr_icon = "mdi:hvac"
    _attr_has_entity_name = True
    _attr_name = "Ventilation Mode"
    _attr_options = list(OPTION_TO_MODE.keys())

    def __init__(self, coordinator: MadokaCoordinator) -> None:
        super().__init__(coordinator)
        self._address = coordinator.address
        self._attr_unique_id = f"{self._address}_ventilation_mode"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._address)},
            "name": f"Madoka {self._address}",
            "manufacturer": "DAIKIN",
            "model": "VAM-FC9",
        }

    @property
    def current_option(self) -> str | None:
        """Return the current ventilation mode."""
        mode = self.coordinator.state.ventilation_mode
        if mode is None:
            return None
        return MODE_TO_OPTION.get(mode)

    async def async_select_option(self, option: str) -> None:
        """Set the ventilation mode."""
        mode = OPTION_TO_MODE.get(option)
        if mode is None:
            return
        current_rate = (
            self.coordinator.state.ventilation_rate
            or VentilationRate.AUTO
        )
        await self.coordinator.async_set_ventilation(mode, current_rate)
