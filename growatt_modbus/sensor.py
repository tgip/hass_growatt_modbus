"""Sensor platform for Growatt Modbus."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    )
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

import logging
from datetime import timedelta
import inspect

from pymodbus.client import AsyncModbusTcpClient

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DEFAULT_REGISTERS,
    DEFAULT_MONITOR_INTERVAL,
    DEFAULT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up sensors."""
    data = entry.data

    host = data.get("host")
    port = data.get("port", DEFAULT_PORT)
    unit_id = data.get("unit", DEFAULT_UNIT_ID)
    name = data.get("name", "Growatt")
    
    # Get update interval and registers from config, fall back to defaults
    update_interval = data.get("update_interval", DEFAULT_MONITOR_INTERVAL)
    registers = data.get("registers", DEFAULT_REGISTERS)
    timeout = data.get("timeout", DEFAULT_TIMEOUT)

    client = AsyncModbusTcpClient(host=host, port=port, timeout=timeout)
    last_known_data = {
        "voltage": None,
        "current": None,
        "power": None,
    }

    async def try_call(fn, *args, **kwargs):
        """Try to call a function, return None if it fails."""
        try:
            return await fn(*args, **kwargs)
        except (TypeError, AttributeError):
            return None

    async def read_reg_compat(addr, unit):
        """Read register with compatible API across pymodbus versions."""
        candidates = []
        for name in ("read_input_registers", "read_holding_registers", "read_registers", "read"):
            if hasattr(client, name):
                candidates.append(getattr(client, name))

        # For each candidate, try various common arg patterns until one works
        for fn in candidates:
            # Try patterns from most-specific to least
            for args in (
                (addr, 1, unit),        # addr, count, unit
                (addr, 1),              # addr, count
                (addr, unit),           # addr, unit
                (addr,),                # addr
            ):
                res = await try_call(fn, *args)
                if res is not None:
                    return res

            # Try keyword 'unit' variants
            sig = inspect.signature(fn)
            if "unit" in sig.parameters:
                res = await try_call(fn, addr, 1, unit=unit)
                if res is not None:
                    return res

        raise RuntimeError("No compatible register-read method found for this pymodbus client.")

    async def async_update_data():
        """Fetch data from inverter."""
        nonlocal last_known_data
        
        try:
            await client.connect()
            
            # Read voltage and current from the registers
            regs = []
            for addr in registers:
                result = await read_reg_compat(addr, unit_id)
                
                if result is None or not hasattr(result, "registers") or len(result.registers) < 1:
                    raise RuntimeError(f"No data from register {addr}")
                
                regs.append(result.registers[0])

            voltage = regs[0] / 10  # 0.1 V scaling
            current = regs[1] / 10  # 0.1 A scaling
            power = voltage * current  # Calculate power

            data = {
                "voltage": voltage,
                "current": current,
                "power": power,
            }
            
            # Update last known values on successful read
            last_known_data = data.copy()
            _LOGGER.debug("Successfully read Growatt data: %s", data)
            
            return data

        except Exception as err:
            _LOGGER.error("Modbus error: %s. Using last known values.", err)
            # Return last known values instead of empty dict
            return last_known_data.copy()
        
        finally:
            client.close()

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=update_interval),
    )

    await coordinator.async_config_entry_first_refresh()

    sensors = [
        GrowattSensor(coordinator, name, "voltage", "Voltage", "V"),
        GrowattSensor(coordinator, name, "current", "Current", "A"),
        GrowattSensor(coordinator, name, "power", "Power", "W"),
        GrowattDebugSensor(coordinator, name),
    ]

    async_add_entities(sensors)


class GrowattSensor(CoordinatorEntity, SensorEntity):
    """Growatt sensor."""

    def __init__(self, coordinator, device_name, key, name, unit):
        super().__init__(coordinator)
        self._attr_name = f"{device_name} {name}"
        self._key = key
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)


class GrowattDebugSensor(CoordinatorEntity, SensorEntity):
    """Debug sensor showing all raw values."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator)
        self._attr_name = f"{name} Debug Data"
        self._attr_icon = "mdi:chart-line"

    @property
    def native_value(self):
        return "OK"

    @property
    def extra_state_attributes(self):
        return self.coordinator.data
