"""Growatt Modbus integration."""

import logging
from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.core import HomeAssistant

from pymodbus.client import AsyncModbusTcpClient

from .const import DOMAIN, PLATFORMS, DEFAULT_PORT, DEFAULT_TIMEOUT

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration via YAML (not used)."""
    # The integration is configured through the UI, so we simply report success.
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Growatt Modbus from a config entry.

    The connection test is performed **before** any platform is forwarded.
    If the inverter cannot be reached we raise ``ConfigEntryNotReady`` so
    Home Assistant will retry the setup later.
    """
    data = entry.data
    host = data.get("host")
    port = data.get("port", DEFAULT_PORT)
    timeout = data.get("timeout", DEFAULT_TIMEOUT)

    # --------------------------------------------------------------
    # 1. Verify that we can talk to the inverter.
    # --------------------------------------------------------------
    client = AsyncModbusTcpClient(host=host, port=port, timeout=timeout)

    try:
        await client.connect()
        _LOGGER.debug("Successfully connected to Growatt inverter at %s:%s", host, port)

        # Perform a tiny read (register 0) just to be sure the device answers.
        # Adjust the register number if your inverter uses a different one.
        try:
            await client.read_input_registers(0, 1, unit=data.get("unit", 0))
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.debug(
                "Initial register read failed – still considering the connection alive: %s", exc, )
        # ----------------------------------------------------------
        # Close the temporary test connection.
        # ``close`` may be sync or async depending on pymodbus version.
        # ----------------------------------------------------------
        close_fn = getattr(client, "close", None)
        if callable(close_fn):
            result = close_fn()
            if hasattr(result, "__await__"):
                await result

    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error(
            "Failed to connect to Growaat inverter at %s:%s – will retry: %s", host, port, err, )
        # Raising ``ConfigEntryNotReady`` tells HA to retry later.
        raise ConfigEntryNotReady(
            f"Could not connect to Growatt inverter at {host}:{port}"
            ) from err

    # --------------------------------------------------------------
    # 2. Store the verified client (and raw entry data) for the platforms.
    # --------------------------------------------------------------
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,  # reusable Modbus client
        "data": entry.data,  # keep original config data handy
        }

    # --------------------------------------------------------------
    # 3. Forward the config entry to the platforms (sensor, switch, …)
    # --------------------------------------------------------------
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Platforms are asked to remove their entities first; when that succeeds
    we also clean‑up the stored client.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Close the persistent client (again handling sync/async flavours)
        stored = hass.data[DOMAIN].pop(entry.entry_id, {})
        client = stored.get("client")
        if client:
            close_fn = getattr(client, "close", None)
            if callable(close_fn):
                result = close_fn()
                if hasattr(result, "__await__"):
                    await result

    return unload_ok