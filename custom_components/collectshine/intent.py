"""The "find me a record" intent, and the service behind it."""

from __future__ import annotations

import logging
from typing import Any, ClassVar

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import intent

from .api import CannotConnect, CollectShineError, FindResult
from .const import (
    ATTR_QUERY,
    CONF_POWER_ON,
    DEFAULT_POWER_ON,
    DOMAIN,
    INTENT_FIND_RECORD,
    SERVICE_FIND_RECORD,
)

_LOGGER = logging.getLogger(__name__)


def _first_coordinator(hass: HomeAssistant):
    """The base station to ask.

    Households have one shelf far more often than several, and an intent carries no way to say
    which. Rather than refusing to answer at all, the first configured base station is used —
    and a second one is a real limitation worth naming in the README rather than papering over.
    """
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        return entry.runtime_data

    return None


async def _find(hass: HomeAssistant, query: str) -> FindResult:
    coordinator = _first_coordinator(hass)

    if coordinator is None:
        raise CannotConnect("No CollectShine base station is set up.")

    power_on = coordinator.config_entry.options.get(CONF_POWER_ON, DEFAULT_POWER_ON)
    result = await coordinator.client.find(query, act=True, power_on=power_on)

    # Finding a record changes what the shelf is showing, and may have switched the lights on.
    await coordinator.async_request_refresh()

    return result


class FindRecordIntentHandler(intent.IntentHandler):
    """Answer "find Kind of Blue" by lighting it on the shelf."""

    intent_type = INTENT_FIND_RECORD
    description = "Find a record in the collection and light it up on the shelf"
    slot_schema: ClassVar[dict[Any, Any]] = {vol.Required("name"): cv.string}

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        slots = self.async_validate_slots(intent_obj.slots)
        query = slots["name"]["value"]

        response = intent_obj.create_response()

        try:
            result = await _find(intent_obj.hass, query)
        except CollectShineError as err:
            _LOGGER.debug("CollectShine could not answer %r: %s", query, err)
            response.async_set_speech("I couldn't reach the record shelf.")
            return response

        # Spoken verbatim. The base station decides both which record it is and how sure it is,
        # and the sentence is the visible half of that same decision — a shelf that is switched
        # off, in particular, says so here and nowhere else.
        response.async_set_speech(result.speech)
        response.async_set_speech_slots(
            {
                "outcome": result.outcome,
                "spotlight": result.spotlight,
                "lit": result.lit,
                "release_id": result.release.id if result.release else None,
                "title": result.release.title if result.release else None,
                "artist": result.release.artist if result.release else None,
            }
        )

        return response


async def async_setup_intents(hass: HomeAssistant) -> None:
    """Register the intent and the service that shares its behaviour."""
    intent.async_register(hass, FindRecordIntentHandler())

    async def handle_find_record(call: ServiceCall) -> dict[str, object]:
        result = await _find(hass, call.data[ATTR_QUERY])

        return {
            "outcome": result.outcome,
            # `outcome` says the sentence was resolved to one record; these say whether the
            # shelf actually showed it. An automation that lights a lamp or sends a notification
            # on every "matched" fires just as happily over a record that was never lit.
            "spotlight": result.spotlight,
            "lit": result.lit,
            "speech": result.speech,
            "release": (
                {
                    "id": result.release.id,
                    "artist": result.release.artist,
                    "title": result.release.title,
                }
                if result.release
                else None
            ),
            "candidates": [
                {"id": c.id, "artist": c.artist, "title": c.title} for c in result.candidates
            ],
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_FIND_RECORD,
        handle_find_record,
        schema=vol.Schema({vol.Required(ATTR_QUERY): cv.string}),
        # Returns a response so an automation can branch on an ambiguous answer instead of
        # assuming every request lit something.
        supports_response=SupportsResponse.OPTIONAL,
    )
