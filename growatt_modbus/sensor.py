"""Sensor platform for Growatt Modbus."""

from __future__ import annotations

import inspect
import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity, DataUpdateCoordinator,
    )

from .const import (
    DOMAIN, DEFAULT_MONITOR_INTERVAL, DEFAULT_REGISTERS, DEFAULT_UNIT_ID,
    )

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities
        ) -> None:
    """Set up sensors from a config entry.

    The Modbus client is created and tested in ``__init__.py``; here we only
    retrieve the already‑verified client from ``hass.data``.
    """
    data = entry.data

    # -----------------------------------------------------------------
    # 1️⃣ Retrieve the reusable client that was stored by __init__.py
    # -----------------------------------------------------------------
    client = hass.data[DOMAIN][entry.entry_id]["client"]

    # -----------------------------------------------------------------
    # 2️⃣ Gather configuration values (with defaults)
    # -----------------------------------------------------------------
    name = data.get("name", "Growatt")
    unit_id = data.get("unit", DEFAULT_UNIT_ID)

    update_interval = data.get("update_interval", DEFAULT_MONITOR_INTERVAL)
    registers = data.get("registers", DEFAULT_REGISTERS)

    # Keep the last successful reading so we can fall back on errors
    last_known_data = {"voltage": None, "current": None, "power": None}

    # -----------------------------------------------------------------
    # Helper: try a coroutine and swallow the typical attribute‑type errors
    # -----------------------------------------------------------------
    async def try_call(fn, *args, **kwargs):
        """Call a coroutine, return None on TypeError / AttributeError."""
        try:
            return await fn(*args, **kwargs)
        except (TypeError, AttributeError):
            return None

    # -----------------------------------------------------------------
    # Helper: read a register using any compatible pymodbus API
    # -----------------------------------------------------------------
    async def read_reg_compat(addr: int, unit: int):
        """Read a register with the best‑matching method on the client."""
        candidates = [getattr(client, name) for name in
            ("read_input_registers", "read_holding_registers", "read_registers", "read",) if hasattr(client, name)]

        for fn in candidates:
            # Try the most common signatures first
            for args in ((addr, 1, unit),  # addr, count, unit
                         (addr, 1),  # addr, count
                         (addr, unit),  # addr, unit
                         (addr,),  # addr only
                    ):
                result = await try_call(fn, *args)
                if result is not None:
                    return result

            # Some versions expose a ``unit=`` keyword
            sig = inspect.signature(fn)
            if "unit" in sig.parameters:
                result = await try_call(fn, addr, 1, unit=unit)
                if result is not None:
                    return result

        raise RuntimeError("No compatible register‑read method found for this client.")

    # -----------------------------------------------------------------
    # Coordinator update – fetch fresh data from the inverter
    # -----------------------------------------------------------------
    async def async_update_data():
        """Fetch the latest values from the inverter."""
        nonlocal last_known_data

        try:
            await client.connect()

            regs = []
            for addr in registers:
                result = await read_reg_compat(addr, unit_id)

                if (result is None or not hasattr(result, "registers") or len(result.registers) < 1):
                    raise RuntimeError(f"No data from register {addr}")

                regs.append(result.registers[0])

            # Growatt uses a 0.1 scaling factor for voltage & current
            voltage = regs[0] / 10.0  # V
            current = regs[1] / 10.0  # A
            power = voltage * current  # W

            data = {"voltage": voltage, "current": current, "power": power}
            last_known_data = data.copy()
            _LOGGER.debug("Successfully read Growatt data: %s", data)
            return data

        except Exception as err:  # pragma: no cover – exercised in integration tests
            _LOGGER.error("Modbus error: %s. Using last known values.", err)
            return last_known_data.copy()

        finally:
            # -------------------------------------------------------------
            # Close the TCP connection.
            # ``close`` may be sync or async depending on pymodbus version.
            # -------------------------------------------------------------
            close_fn = getattr(client, "close", None)
            if callable(close_fn):
                result = close_fn()
                if hasattr(result, "__await__"):
                    await result

    # -----------------------------------------------------------------
    # Set up the DataUpdateCoordinator
    # -----------------------------------------------------------------
    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name=DOMAIN, update_method=async_update_data,
        update_interval=timedelta(seconds=update_interval), )

    # Perform the first poll before any entities are added
    await coordinator.async_config_entry_first_refresh()

    # -----------------------------------------------------------------
    # Create the sensor entities
    # -----------------------------------------------------------------
    sensors = [GrowattSensor(coordinator, name, "voltage", "Voltage", "V"),
        GrowattSensor(coordinator, name, "current", "Current", "A"),
        GrowattSensor(coordinator, name, "power", "Power", "W"), GrowattDebugSensor(coordinator, name), ]

    async_add_entities(sensors)

class GrowattSensor(CoordinatorEntity, SensorEntity):
    """Generic Growatt measurement sensor."""

    def __init__(
            self, coordinator, device_name: str, key: str, friendly_name: str, unit: str, ) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{device_name} {friendly_name}"
        self._key = key
        self._attr_native_unit_of_measurement = unit

        # ---- device class handling (measurement) ----
        if key == "voltage":
            self._attr_device_class = SensorDeviceClass.VOLTAGE
        elif key == "current":
            self._attr_device_class = SensorDeviceClass.CURRENT
        elif key == "power":
            self._attr_device_class = SensorDeviceClass.POWER
        # AttributeError: type object 'SensorDeviceClass' has no attribute 'MEASUREMENT'
        # else:
        #    self._attr_device_class = SensorDeviceClass.MEASUREMENT
        else:
            # No explicit generic class; leaving it unset yields the default
            self._attr_device_class = None

    @property
    def native_value(self):
        """Return the latest value from the coordinator."""
        return self.coordinator.data.get(self._key)

class GrowattDebugSensor(CoordinatorEntity, SensorEntity):
    """Debug sensor exposing the full raw payload."""

    def __init__(self, coordinator, device_name: str) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{device_name} Debug Data"
        self._attr_icon = "mdi:chart-line"
        # self._attr_device_class = SensorDeviceClass.MEASUREMENT
        # No specific device class needed for a generic debug sensor
        self._attr_device_class = None

    @property
    def native_value(self):
        """Static placeholder – the real data lives in attributes."""
        return "OK"

    @property
    def extra_state_attributes(self):
        """Expose the raw dictionary returned by the coordinator."""
        return self.coordinator.data
