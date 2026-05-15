"""Options flow for Growatt Modbus integration with sensor CRUD.

Uses a comma-separated string for registers in the form and parses to list[int].
Supports adding, updating, and removing sensors, with changes written to const.py.
"""

import os
import json
import logging
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_PORT, CONF_TIMEOUT
from .const import SENSORS

_LOGGER = logging.getLogger(__name__)
CONST_FILE_PATH = os.path.join(os.path.dirname(__file__), "const.py")  # Path to const.py

CONF_UNIT_ID = "unit_id"
CONF_REGISTERS = "registers"
CONF_MONITOR_INTERVAL = "monitor_interval"
CONF_SENSOR_ACTION = "sensor_action"
CONF_SENSOR_KEY = "sensor_key"
CONF_SENSOR_DETAILS = "sensor_details"

ACTIONS = ["Add Sensor", "Update Sensor", "Remove Sensor", "View Sensors"]

class GrowattOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for the integration."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Show options form with sensor management functionality."""
        if user_input is not None:
            action = user_input.get(CONF_SENSOR_ACTION)
            if action == "Add Sensor":
                return await self.async_step_add_sensor()
            elif action == "Update Sensor":
                return await self.async_step_update_sensor()
            elif action == "Remove Sensor":
                return await self.async_step_remove_sensor()
            elif action == "View Sensors":
                return await self.async_step_view_sensors()

        # Schema to choose an action
        import voluptuous as vol
        from voluptuous import Required

        schema = vol.Schema(
            {
                Required(CONF_SENSOR_ACTION): vol.In(ACTIONS)
                }
            )

        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_add_sensor(self, user_input=None):
        """Handle adding a new sensor."""
        errors = {}

        if user_input is not None:
            try:
                key = user_input.get(CONF_SENSOR_KEY)
                if key in SENSORS:
                    errors["base"] = "sensor_exists"
                else:
                    SENSORS[key] = {
                        "address": int(user_input["address"]), "name": user_input["name"], "key": key,
                        "friendly_name": user_input["friendly_name"],
                        "scaling_factor": float(user_input["scaling_factor"]), "unit": user_input["unit"],
                        "device_class": user_input["device_class"],
                        }
                    self._save_sensors()
                    return self.async_create_entry(title="Sensor Added", data={})
            except Exception as e:
                _LOGGER.error(f"Failed to add sensor: {e}")
                errors["base"] = "unknown_error"

        # Schema to add a sensor
        import voluptuous as vol
        from voluptuous import Required, Coerce

        schema = vol.Schema(
            {
                Required("name"): str, Required("key"): str, Required("friendly_name"): str,
                Required("address"): Coerce(int), Required("scaling_factor"): Coerce(float), Required("unit"): str,
                Required("device_class"): str,
                }
            )

        return self.async_show_form(step_id="add_sensor", data_schema=schema, errors=errors)

    async def async_step_update_sensor(self, user_input=None):
        """Handle updating an existing sensor."""
        errors = {}

        if user_input is not None:
            try:
                key = user_input.get(CONF_SENSOR_KEY)
                if key not in SENSORS:
                    errors["base"] = "sensor_not_found"
                else:
                    SENSORS[key].update(
                        {
                            "address": int(user_input["address"]), "name": user_input["name"],
                            "friendly_name": user_input["friendly_name"],
                            "scaling_factor": float(user_input["scaling_factor"]), "unit": user_input["unit"],
                            "device_class": user_input["device_class"],
                            }
                        )
                    self._save_sensors()
                    return self.async_create_entry(title="Sensor Updated", data={})
            except Exception as e:
                _LOGGER.error(f"Failed to update sensor: {e}")
                errors["base"] = "unknown_error"

        # Schema to update a sensor
        import voluptuous as vol
        from voluptuous import Required, Coerce

        schema = vol.Schema(
            {
                Required(CONF_SENSOR_KEY): str, Required("name"): str, Required("friendly_name"): str,
                Required("address"): Coerce(int), Required("scaling_factor"): Coerce(float), Required("unit"): str,
                Required("device_class"): str,
                }
            )

        return self.async_show_form(step_id="update_sensor", data_schema=schema, errors=errors)

    async def async_step_remove_sensor(self, user_input=None):
        """Handle removing an existing sensor."""
        errors = {}

        if user_input is not None:
            key = user_input.get(CONF_SENSOR_KEY)
            if key not in SENSORS:
                errors["base"] = "sensor_not_found"
            else:
                del SENSORS[key]
                self._save_sensors()
                return self.async_create_entry(title="Sensor Removed", data={})

        # Schema to remove a sensor
        import voluptuous as vol
        from voluptuous import Required

        schema = vol.Schema(
            {
                Required(CONF_SENSOR_KEY): str
                }
            )

        return self.async_show_form(step_id="remove_sensor", data_schema=schema, errors=errors)

    async def async_step_view_sensors(self, user_input=None):
        """View all sensors."""
        sensors_str = json.dumps(SENSORS, indent=4).replace("{", "").replace("}", "")
        return self.async_create_entry(title="Sensors List", data={"sensors": sensors_str})

    def _save_sensors(self):
        """Save the updated sensors back to const.py."""
        try:
            with open(CONST_FILE_PATH, "r", encoding="utf-8") as file:
                lines = file.readlines()

            # Locate the SENSORS dictionary and replace with updated values
            start_idx = None
            end_idx = None
            for i, line in enumerate(lines):
                if line.strip().startswith("SENSORS = {"):
                    start_idx = i
                if start_idx is not None and line.strip() == "}":
                    end_idx = i
                    break

            if start_idx is None or end_idx is None:
                raise ValueError("SENSORS definition not found in const.py")

            # Build updated SENSORS data
            sensors_dict_str = json.dumps(SENSORS, indent=4)
            sensors_dict_str = sensors_dict_str.replace('null', 'None').replace('true', 'True').replace(
                'false', 'False'
                )
            new_lines = lines[:start_idx + 1]
            new_lines.append("    " + sensors_dict_str[1:-1].replace("\n", "\n    ") + "\n")
            new_lines.extend(lines[end_idx:])

            # Write to file
            with open(CONST_FILE_PATH, "w", encoding="utf-8") as file:
                file.writelines(new_lines)

            _LOGGER.info("Successfully updated SENSORS in const.py.")
        except Exception as e:
            _LOGGER.error(f"Failed to save SENSORS to const.py: {e}")
            raise
