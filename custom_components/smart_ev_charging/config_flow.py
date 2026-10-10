"""Config flow for Smart EV Charging."""

from __future__ import annotations

from typing import Any

import probatio

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import (
    CONF_BATTERY_CAPACITY_KWH,
    CONF_NAME,
    CONF_PRICE_ENTITY,
    CONF_SOC_ENTITY,
    DEFAULT_NAME,
    DOMAIN,
    PRICE_ATTRIBUTE,
)

STEP_USER_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_NAME, default=DEFAULT_NAME): TextSelector(),
        probatio.Required(CONF_SOC_ENTITY): EntitySelector(
            EntitySelectorConfig(domain=["sensor", "number", "input_number"])
        ),
        probatio.Required(CONF_BATTERY_CAPACITY_KWH): NumberSelector(
            NumberSelectorConfig(
                min=1.0,
                max=250.0,
                step=0.1,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="kWh",
            )
        ),
        probatio.Optional(CONF_PRICE_ENTITY): EntitySelector(
            EntitySelectorConfig(domain=["sensor"])
        ),
    }
)

PRICE_OPTIONS_SCHEMA = probatio.Schema(
    {
        probatio.Optional(CONF_PRICE_ENTITY): EntitySelector(
            EntitySelectorConfig(domain=["sensor"])
        )
    }
)


def _valid_price_entity(hass: HomeAssistant, entity_id: str | None) -> bool:
    """Return whether an entity exposes a supported prices attribute."""
    if not entity_id:
        return True

    state = hass.states.get(entity_id)
    if state is None:
        return False

    return isinstance(state.attributes.get(PRICE_ATTRIBUTE), list)


class SmartEVChargingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart EV Charging."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return SmartEVChargingOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            price_entity = user_input.get(CONF_PRICE_ENTITY)
            if not _valid_price_entity(self.hass, price_entity):
                errors[CONF_PRICE_ENTITY] = "invalid_price_entity"
            else:
                await self.async_set_unique_id(user_input[CONF_SOC_ENTITY])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class SmartEVChargingOptionsFlow(config_entries.OptionsFlow):
    """Configure optional Smart EV Charging providers."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure the electricity price source."""
        errors: dict[str, str] = {}

        if user_input is not None:
            price_entity = user_input.get(CONF_PRICE_ENTITY)
            if not _valid_price_entity(self.hass, price_entity):
                errors[CONF_PRICE_ENTITY] = "invalid_price_entity"
            else:
                new_options = dict(self.config_entry.options)
                if price_entity:
                    new_options[CONF_PRICE_ENTITY] = price_entity
                else:
                    # An explicit empty option masks a price source that may
                    # have been selected during the initial config flow.
                    new_options[CONF_PRICE_ENTITY] = ""

                return self.async_create_entry(data=new_options)

        current_price_entity = self.config_entry.options.get(
            CONF_PRICE_ENTITY,
            self.config_entry.data.get(CONF_PRICE_ENTITY),
        )
        suggested = (
            {CONF_PRICE_ENTITY: current_price_entity}
            if current_price_entity
            else {}
        )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                PRICE_OPTIONS_SCHEMA, suggested
            ),
            errors=errors,
        )
