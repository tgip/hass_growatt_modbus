"""Options flow for Growatt Modbus integration.

Uses a comma-separated string for registers in the form and parses to list[int].
Attempts to fetch current register values to provide suggestions (non-fatal).
"""

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_PORT, CONF_TIMEOUT
from .const import DEFAULT_PORT, DEFAULT_MONITOR_INTERVAL, DEFAULT_TIMEOUT
from .pyclient import ModbusReader

CONF_UNIT_ID = "unit_id"
CONF_REGISTERS = "registers"
CONF_MONITOR_INTERVAL = "monitor_interval"

class GrowattOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for the integration."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Show options form; show register values as suggested info if available."""
        errors = {}

        if user_input is not None:
            regs_raw = user_input.get(CONF_REGISTERS, "")
            try:
                regs = [int(x.strip()) for x in regs_raw.split(",") if x.strip() != ""]
            except ValueError:
                errors["base"] = "invalid_registers"
                regs = []

            if len(regs) < 2:
                errors["base"] = "invalid_registers"

            if not errors:
                user_input[CONF_REGISTERS] = regs
                return self.async_create_entry(title="", data=user_input)

        # Try to fetch current register readings to show as context (non-fatal)
        try:
            data = self.config_entry.data
            reader = ModbusReader(
                host=data[CONF_HOST], port=data.get(CONF_PORT, DEFAULT_PORT),
                timeout=data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
                )
            await reader.async_connect()
            regs_existing = data.get(CONF_REGISTERS, [3, 4])
            v = await reader.async_read_register(regs_existing[0], data.get(CONF_UNIT_ID, 1))
            c = await reader.async_read_register(regs_existing[1], data.get(CONF_UNIT_ID, 1))
            await reader.async_close()
            suggested_v = v
            suggested_c = c
        except Exception:
            suggested_v = None
            suggested_c = None

        import voluptuous as vol
        from voluptuous import Required, Optional, Coerce

        default_regs_csv = ",".join(str(x) for x in self.config_entry.data.get(CONF_REGISTERS, [3, 4]))

        schema = vol.Schema(
            {
                Required(CONF_NAME, default=self.config_entry.data.get(CONF_NAME)): str,
                Required(CONF_HOST, default=self.config_entry.data.get(CONF_HOST)): str,
                Required(CONF_PORT, default=self.config_entry.data.get(CONF_PORT, DEFAULT_PORT)): Coerce(int),
                Required(CONF_UNIT_ID, default=self.config_entry.data.get(CONF_UNIT_ID, 1)): Coerce(int),
                Required(CONF_REGISTERS, default=default_regs_csv): str, Optional(
                CONF_MONITOR_INTERVAL,
                default=self.config_entry.data.get(CONF_MONITOR_INTERVAL, DEFAULT_MONITOR_INTERVAL)
                ): Coerce(int),
                Optional(CONF_TIMEOUT, default=self.config_entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)): Coerce(int),
                }
            )

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
