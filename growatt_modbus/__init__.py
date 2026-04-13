"""Growatt Modbus integration."""

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from pymodbus.client import AsyncModbusTcpClient

from .const import DOMAIN, PLATFORMS, DEFAULT_PORT, DEFAULT_TIMEOUT

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the integration via YAML (not used)."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Growatt Modbus from a config entry."""

    data = entry.data
    host = data.get("host")
    port = data.get("port", DEFAULT_PORT)
    timeout = data.get("timeout", DEFAULT_TIMEOUT)

    # Test connection before setting up platforms
    client = AsyncModbusTcpClient(host=host, port=port, timeout=timeout)

    try:
        await client.connect()
        _LOGGER.debug("Successfully connected to a Growatt inverter at %s:%s", host, port)
        client.close()
    except Exception as err:
        _LOGGER.error("Failed to connect to a Growatt inverter at %s:%s: %s", host, port, err)
        raise ConfigEntryNotReady(f"Could not connect to {host}:{port}") from err

    # Store entry data for later use
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Set up platforms after successful connection
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
