"""Fan platform for Daikin VAM-FC9 ventilation rate control.

Exposes a FanEntity with preset modes (auto/low/high) to control the
ventilation rate of VAM-FC9 recuperation units.  Only created when the
device is detected as a ventilation unit during startup probe.

The ventilation rate is read via CMD 0x0031 and set via CMD 0x4031
(param 0x21).  Power on/off is shared with the main thermostat.
"""
from __future__ import annotations

import logging

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MadokaCoordinator
from .madoka_protocol import VentilationMode, VentilationRate

_LOGGER = logging.getLogger(__name__)

RATE_TO_PRESET = {
    VentilationRate.AUTO: "auto",
    VentilationRate.LOW: "low",
    VentilationRate.HIGH: "high",
}

PRESET_TO_RATE = {v: k for k, v in RATE_TO_PRESET.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Daikin ventilation fan from a config entry."""
    coordinator: MadokaCoordinator = hass.data[DOMAIN][entry.entry_id]
    if not coordinator.state.is_ventilation_device:
        return
    async_add_entities([DaikinMadokaVentilationFan(coordinator)])


class DaikinMadokaVentilationFan(
    CoordinatorEntity[MadokaCoordinator], FanEntity
):
    """Fan entity to control ventilation rate (auto/low/high)."""

    _attr_icon = "mdi:air-filter"
    _attr_has_entity_name = True
    _attr_name = "Ventilation"
    _attr_supported_features = (
        FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = list(PRESET_TO_RATE.keys())

    def __init__(self, coordinator: MadokaCoordinator) -> None:
        super().__init__(coordinator)
        self._address = coordinator.address
        self._attr_unique_id = f"{self._address}_ventilation_fan"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._address)},
            "name": f"Madoka {self._address}",
            "manufacturer": "DAIKIN",
            "model": "VAM-FC9",
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if the ventilation unit is on."""
        return self.coordinator.state.power_on

    @property
    def preset_mode(self) -> str | None:
        """Return the current ventilation rate as a preset mode."""
        rate = self.coordinator.state.ventilation_rate
        if rate is None:
            return None
        return RATE_TO_PRESET.get(rate)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the ventilation rate."""
        rate = PRESET_TO_RATE.get(preset_mode)
        if rate is None:
            return
        current_mode = (
            self.coordinator.state.ventilation_mode
            or VentilationMode.AUTO
        )
        await self.coordinator.async_set_ventilation(current_mode, rate)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the ventilation unit on."""
        await self.coordinator.async_set_power(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the ventilation unit off."""
        await self.coordinator.async_set_power(False)
