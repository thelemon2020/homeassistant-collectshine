"""The one nudge this integration gives, and why it needs to exist.

A finished config flow leaves an owner with a light, some sensors and two buttons — and no way
to ask for a record out loud, which is the entire point of the thing. Assist matches sentences,
and sentences arrive one of two ways: a YAML file under `config/custom_sentences/<language>/`,
or a sentence trigger on an automation. HACS can deliver neither, because it installs
`custom_components/` and nothing else.

So the gap is structural rather than a documentation oversight, and it lands on the owner at
exactly the moment they have stopped reading instructions. This notification is what closes it:
one link, which imports a blueprint that carries the sentences with it.

Shown once per base station. An owner who has been told and moved on has made a decision.
"""

from __future__ import annotations

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant

from .const import BLUEPRINT_IMPORT_URL, DATA_SENTENCES_PROMPTED, DOMAIN
from .coordinator import CollectShineConfigEntry

NOTIFICATION_ID = f"{DOMAIN}_sentences"

_TITLE = "Ask CollectShine for a record"

_MESSAGE = f"""
**{{name}} is connected.** One step left before you can ask for a record out loud: Home Assistant
needs to know the sentences to listen for, and that is not something the integration can install
for you.

**[Add the voice sentences]({BLUEPRINT_IMPORT_URL})**

That imports a blueprint. Create an automation from it, then try *find Kind of Blue* — the words
go to your base station, which decides which record you meant.

Already using an LLM voice assistant? It needs no sentences; ask it in your own words instead.
"""


async def async_prompt_for_sentences(hass: HomeAssistant, entry: CollectShineConfigEntry) -> None:
    """Tell the owner, once, that voice needs sentences and hand them the one-click way in."""
    if entry.data.get(DATA_SENTENCES_PROMPTED):
        return

    persistent_notification.async_create(
        hass,
        _MESSAGE.format(name=entry.title),
        title=_TITLE,
        notification_id=f"{NOTIFICATION_ID}_{entry.entry_id}",
    )

    # Recorded before anything can go wrong afterwards, because the failure worth avoiding is
    # nagging an owner on every restart — not missing them once.
    hass.config_entries.async_update_entry(entry, data={**entry.data, DATA_SENTENCES_PROMPTED: True})
