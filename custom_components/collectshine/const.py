"""Constants for the CollectShine integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final
from urllib.parse import quote

DOMAIN: Final = "collectshine"

# The base station stamps a contract version into GET /api/v1/voice/state and into its mDNS
# advertisement. The two sides ship from different repositories on different cycles, so this is
# what turns "your base station is older than this integration expects" into something the config
# flow can say out loud rather than a KeyError three layers down.
SUPPORTED_API_VERSION: Final = 1

# One request per tick, composed server-side. The base station is a Raspberry Pi driving LEDs;
# polling it harder buys nothing, and a shelf's state does not change without somebody doing it.
SCAN_INTERVAL: Final = timedelta(seconds=30)

REQUEST_TIMEOUT: Final = 10

CONF_POWER_ON: Final = "power_on"

# Default on, while the API defaults it off. Both are right: an API should not switch on hardware
# nobody asked it to, but a person who says "find Kind of Blue" wants to see Kind of Blue, and a
# spotlight on a dark shelf is invisible.
DEFAULT_POWER_ON: Final = True

INTENT_FIND_RECORD: Final = "CollectShineFindRecord"

SERVICE_FIND_RECORD: Final = "find_record"
ATTR_QUERY: Final = "query"

# HACS installs `custom_components/` and nothing else, so it cannot deliver the sentences that
# make the intent above reachable by voice — that step is manual for every owner, on a system
# with no filesystem access out of the box. A blueprint is the way out: one click imports it,
# and a sentence trigger needs no files at all. Hence the nudge in onboarding.py, which is the
# only thing standing between a finished config flow and an owner who never learns voice exists.
BLUEPRINT_URL: Final = (
    "https://github.com/thelemon2020/homeassistant-collectshine/blob/main/"
    "blueprints/automation/collectshine/find_record.yaml"
)

# Derived rather than written out twice: the encoded form is unreadable, and a link that quietly
# points at a different file than the one above is the kind of thing nobody notices for months.
BLUEPRINT_IMPORT_URL: Final = (
    "https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=" + quote(BLUEPRINT_URL, safe="")
)

# Written into the config entry once the owner has been told. Kept in `data` rather than
# `options` because options are the owner's to change and this is bookkeeping.
DATA_SENTENCES_PROMPTED: Final = "sentences_prompted"

# mDNS TXT keys published by App\Console\Commands\InstallCommand::avahiServiceFile().
TXT_API: Final = "api"
TXT_DEVICE: Final = "device"
