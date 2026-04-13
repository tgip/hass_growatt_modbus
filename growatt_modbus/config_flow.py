"""Config flow for Growatt Modbus (TCP) integration.

Uses a comma-separated string for the registers field (e.g. "3,4")
so voluptuous_serialize can convert the schema. The string is parsed
into a list[int] and stored in the config entry.
"""

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_PORT, CONF_TIMEOUT
from .const import DOMAIN, DEFAULT_PORT, DEFAULT_UNIT_ID, DEFAULT_REGISTERS, DEFAULT_MONITOR_INTERVAL, DEFAULT_TIMEOUT
from .pyclient import ModbusReader

CONF_UNIT_ID = "unit_id"
CONF_REGISTERS = "registers"  # stored as list[int]
CONF_MONITOR_INTERVAL = "monitor_interval"

class GrowattModbusFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Growatt Modbus."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Initial form to add a new inverter."""
        errors = {}

        if user_input is not None:
            # Parse registers CSV string into list[int]
            regs_raw = user_input.get(CONF_REGISTERS, "")
            try:
                regs = [int(x.strip()) for x in regs_raw.split(",") if x.strip() != ""]
            except ValueError:
                errors["base"] = "invalid_registers"
                regs = []

            if len(regs) < 2:
                errors["base"] = "invalid_registers"

            if not errors:
                reader = ModbusReader(
                    host=user_input[CONF_HOST],
                    port=user_input.get(CONF_PORT, DEFAULT_PORT),
                    timeout=user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                )
                try:
                    await reader.async_connect()
                    v = await reader.async_read_register(regs[0], user_input.get(CONF_UNIT_ID, DEFAULT_UNIT_ID))
                    c = await reader.async_read_register(regs[1], user_input.get(CONF_UNIT_ID, DEFAULT_UNIT_ID))
                    await reader.async_close()
                    if v is None or c is None:
                        errors["base"] = "no_data"
                except Exception:
                    errors["base"] = "connection_failed"

            if not errors:
                title = user_input.get(CONF_NAME) or f"Growatt {user_input[CONF_HOST]}"
                data = {
                    CONF_NAME: user_input.get(CONF_NAME),
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
                    CONF_UNIT_ID: user_input.get(CONF_UNIT_ID, DEFAULT_UNIT_ID),
                    CONF_REGISTERS: regs,
                    CONF_MONITOR_INTERVAL: user_input.get(CONF_MONITOR_INTERVAL, DEFAULT_MONITOR_INTERVAL),
                    CONF_TIMEOUT: user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                }
                return self.async_create_entry(title=title, data=data)

        import voluptuous as vol
        from voluptuous import Required, Optional, Coerce

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                Required(CONF_NAME, default="Growatt Inverter"): str,
                Required(CONF_HOST): str,
                Optional(CONF_PORT, default=DEFAULT_PORT): Coerce(int),
                Optional(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): Coerce(int),
                Optional(CONF_REGISTERS, default="{},{}".format(*DEFAULT_REGISTERS)): str,
                Optional(CONF_MONITOR_INTERVAL, default=DEFAULT_MONITOR_INTERVAL): Coerce(int),
                Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): Coerce(int),
            }),
            errors=errors,
        )