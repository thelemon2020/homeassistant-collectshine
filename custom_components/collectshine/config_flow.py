"""Config flow for CollectShine."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import (
    CannotConnect,
    CollectShineClient,
    InvalidAuth,
    SubscriptionRequired,
    UnsupportedVersion,
)
from .const import (
    CONF_POWER_ON,
    DEFAULT_POWER_ON,
    DOMAIN,
    SUPPORTED_API_VERSION,
    TXT_API,
    TXT_DEVICE,
)

_LOGGER = logging.getLogger(__name__)


class CollectShineConfigFlow(ConfigFlow, domain=DOMAIN):
    """Walk the owner from "there is a base station here" to a working integration."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> CollectShineOptionsFlow:
        return CollectShineOptionsFlow()

    def __init__(self) -> None:
        self._host: str | None = None
        self._name: str = "CollectShine"
        self._firmware: str | None = None

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """A base station announced itself on the network.

        The address is taken rather than the `.local` name on purpose. Home Assistant has already
        resolved the name to get here, and `.local` resolution from inside a container is not
        dependable — the CollectShine mobile app learned the same lesson and switched to the
        address it gets from the heartbeat.
        """
        properties = {
            key.lower(): value for key, value in (discovery_info.properties or {}).items()
        }

        advertised = properties.get(TXT_API)
        if advertised is not None and str(advertised).isdigit() and int(advertised) > SUPPORTED_API_VERSION:
            return self.async_abort(reason="unsupported_version")

        self._host = str(discovery_info.ip_address)
        self._name = str(properties.get(TXT_DEVICE) or discovery_info.hostname.removesuffix(".local."))

        # The mDNS name is stable per device and survives a DHCP lease moving; the real device id
        # replaces it once there is a token to read it with.
        await self.async_set_unique_id(self._name)
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})

        try:
            self._firmware = (await self._probe(self._host)).get("app_version")
        except CannotConnect:
            return self.async_abort(reason="cannot_connect")

        self.context["title_placeholders"] = {"name": self._name}

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="zeroconf_confirm",
                description_placeholders={
                    "name": self._name,
                    "host": self._host or "",
                    "firmware": self._firmware or "unknown",
                },
            )

        return await self.async_step_token()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Type in an address, for a network where mDNS does not carry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip().removeprefix("http://").removeprefix("https://").rstrip("/")

            try:
                status = await self._probe(host)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                self._host = host
                self._firmware = status.get("app_version")
                return await self.async_step_token()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )

    async def async_step_token(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the agent token that lets this hub speak to the shelf."""
        errors: dict[str, str] = {}
        description: dict[str, str] = {"name": self._name, "error_detail": ""}

        if user_input is not None:
            assert self._host is not None
            client = CollectShineClient(
                async_get_clientsession(self.hass), self._host, user_input[CONF_TOKEN]
            )

            try:
                state = await client.state()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except SubscriptionRequired as err:
                errors["base"] = "subscription_required"
                # The base station tells a lapsed subscription apart from one it has never synced,
                # and writes a sentence for each. Showing it verbatim beats guessing which it was.
                description["error_detail"] = str(err)
            except UnsupportedVersion:
                errors["base"] = "unsupported_version"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                if state.device_id:
                    await self.async_set_unique_id(state.device_id, raise_on_progress=False)
                    self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})

                return self.async_create_entry(
                    title=state.device_name,
                    data={CONF_HOST: self._host, CONF_TOKEN: user_input[CONF_TOKEN]},
                )

        return self.async_show_form(
            step_id="token",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
            description_placeholders=description,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """The token stopped working — almost always because the owner revoked it."""
        self._host = entry_data[CONF_HOST]
        self._name = self.context.get("title_placeholders", {}).get("name", "CollectShine")

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        description: dict[str, str] = {"name": self._name, "error_detail": ""}

        if user_input is not None:
            assert self._host is not None
            client = CollectShineClient(
                async_get_clientsession(self.hass), self._host, user_input[CONF_TOKEN]
            )

            try:
                await client.state()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except SubscriptionRequired as err:
                errors["base"] = "subscription_required"
                description["error_detail"] = str(err)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={CONF_TOKEN: user_input[CONF_TOKEN]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
            description_placeholders=description,
        )

    async def _probe(self, host: str) -> dict[str, Any]:
        """Confirm a base station is really there, before asking for a credential.

        `system/status` needs no token, so the confirmation step can name the device and its
        firmware rather than showing an IP address and hoping.
        """
        return await CollectShineClient(async_get_clientsession(self.hass), host).probe()


class CollectShineOptionsFlow(OptionsFlow):
    """The one choice worth offering: whether finding a record may switch the lights on."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POWER_ON,
                        default=self.config_entry.options.get(CONF_POWER_ON, DEFAULT_POWER_ON),
                    ): bool
                }
            ),
        )
