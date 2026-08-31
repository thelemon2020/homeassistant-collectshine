"""Constants for the CollectShine integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

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

# mDNS TXT keys published by App\Console\Commands\InstallCommand::avahiServiceFile().
TXT_API: Final = "api"
TXT_DEVICE: Final = "device"
