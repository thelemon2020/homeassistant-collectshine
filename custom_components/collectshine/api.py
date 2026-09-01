"""HTTP client for a CollectShine base station on the local network."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import REQUEST_TIMEOUT, SUPPORTED_API_VERSION

_LOGGER = logging.getLogger(__name__)


class CollectShineError(Exception):
    """Base class for anything that went wrong talking to a base station."""


class CannotConnect(CollectShineError):
    """The base station could not be reached, or did not answer like one."""


class InvalidAuth(CollectShineError):
    """The token was missing, unknown, or has been revoked."""


class SubscriptionRequired(CollectShineError):
    """The token is good but the owner's CollectShine Plus subscription is not active.

    The base station distinguishes a lapsed subscription from one it has simply never synced —
    a freshly paired device has not had a heartbeat answered yet — and writes a sentence for each.
    That sentence is carried through verbatim rather than reworded here, because telling somebody
    to go and buy a subscription they already have is the wrong answer.
    """

    def __init__(self, message: str, reason: str | None = None) -> None:
        super().__init__(message)
        self.reason = reason


class UnsupportedVersion(CollectShineError):
    """The base station speaks a contract this integration does not."""


@dataclass(slots=True)
class Record:
    """A record, reduced to what a sensor can hold and a service can act on."""

    id: int
    artist: str
    title: str

    @property
    def label(self) -> str:
        return f"{self.artist} — {self.title}" if self.artist else self.title

    @classmethod
    def from_json(cls, data: dict[str, Any] | None) -> Record | None:
        if not data:
            return None
        return cls(
            id=int(data["id"]),
            artist=str(data.get("artist") or ""),
            title=str(data.get("title") or ""),
        )


@dataclass(slots=True)
class Shelf:
    """One LED controller — a shelf, in the words the product uses."""

    id: int
    name: str


@dataclass(slots=True)
class BaseStationState:
    """One poll of GET /api/v1/voice/state."""

    api_version: int
    device_id: str | None
    device_name: str
    firmware: str
    release_count: int
    lights_on: bool
    now_playing: Record | None
    last_played: Record | None
    flip_due: bool
    shelves: list[Shelf]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> BaseStationState:
        device = data.get("device") or {}
        return cls(
            api_version=int(data.get("api_version", 0)),
            device_id=device.get("id"),
            device_name=str(device.get("name") or "CollectShine"),
            firmware=str(device.get("firmware") or "unknown"),
            release_count=int((data.get("collection") or {}).get("releases", 0)),
            lights_on=bool(data.get("lights_on")),
            now_playing=Record.from_json(data.get("now_playing")),
            last_played=Record.from_json(data.get("last_played")),
            flip_due=bool(data.get("flip_due")),
            shelves=[
                Shelf(id=int(s["id"]), name=str(s.get("name") or f"Shelf {s['id']}"))
                for s in data.get("shelves") or []
            ],
        )


@dataclass(slots=True)
class FindResult:
    """What came of asking the shelf to find a record.

    `speech` is written by the base station and read out unchanged. The wording is inseparable
    from the confidence policy that chose it — "I found a few" is only correct because the
    resolver decided the margin was too narrow to act on — so rebuilding the sentence here would
    split one decision across two repositories.
    """

    outcome: str
    speech: str
    release: Record | None
    candidates: list[Record]
    lights_on: bool | None

    #: Whether the record itself got a light, which is a different question from `lights_on` —
    #: that one is only about whether the strip has power. "lit", "not_on_shelf", "unreachable",
    #: or None from a base station older than 0.61.0, which did not report it and sometimes
    #: claimed success when nothing had happened.
    spotlight: str | None

    @property
    def matched(self) -> bool:
        return self.outcome == "matched"

    @property
    def lit(self) -> bool:
        """Whether the owner can actually expect to see something.

        Deliberately conservative about the two unknowns. An older base station sends no
        `spotlight` at all, and its "matched" has always been an intention rather than an
        observation, so it is not treated as proof that a light came on.
        """
        return self.matched and self.spotlight == "lit" and bool(self.lights_on)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> FindResult:
        return cls(
            outcome=str(data.get("outcome") or "not_found"),
            speech=str(data.get("speech") or ""),
            release=Record.from_json(data.get("release")),
            candidates=[
                record
                for candidate in data.get("candidates") or []
                if (record := Record.from_json(candidate)) is not None
            ],
            lights_on=data.get("lights_on"),
            spotlight=(None if (raw := data.get("spotlight")) is None else str(raw)),
        )


class CollectShineClient:
    """Talks to one base station over the LAN.

    Plain HTTP on port 80: nginx on the Pi terminates nothing, and there is no certificate a
    `.local` name on a home network could hold anyway. That is exactly why the endpoints this
    client needs refuse anything arriving from outside the house.
    """

    def __init__(self, session: aiohttp.ClientSession, host: str, token: str | None = None) -> None:
        self._session = session
        self._host = host
        self._token = token

    @property
    def host(self) -> str:
        return self._host

    def _url(self, path: str) -> str:
        return f"http://{self._host}/api/v1/{path.lstrip('/')}"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    async def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            async with self._session.request(
                method,
                self._url(path),
                json=payload,
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                if response.status == 401:
                    raise InvalidAuth("The base station rejected this token.")

                if response.status == 403:
                    body = await self._safely_read(response)
                    # 403 is two different things here: a lapsed subscription, and a request that
                    # arrived from outside the house. Only the first has something useful to say.
                    raise SubscriptionRequired(
                        str(body.get("error") or "This base station refused the request."),
                        reason=body.get("reason"),
                    )

                if response.status >= 400:
                    raise CannotConnect(f"The base station answered {response.status}.")

                return await self._safely_read(response)
        except aiohttp.ClientError as err:
            raise CannotConnect(f"Could not reach {self._host}: {err}") from err
        except TimeoutError as err:
            raise CannotConnect(f"{self._host} did not answer in time.") from err

    @staticmethod
    async def _safely_read(response: aiohttp.ClientResponse) -> dict[str, Any]:
        try:
            # The base station always sends JSON; a non-JSON body means something else is
            # listening on port 80, which is a connection problem rather than a parse problem.
            data = await response.json(content_type=None)
        except ValueError as err:
            raise CannotConnect("That address answered, but not like a base station.") from err

        return data if isinstance(data, dict) else {}

    async def probe(self) -> dict[str, Any]:
        """Confirm a CollectShine base station is at this address, before asking for a token.

        `system/status` carries no authentication, which is what lets the config flow show the
        owner a firmware version on the confirmation step instead of an IP address.
        """
        data = await self._request("GET", "system/status")

        if "app_version" not in data:
            raise CannotConnect("That address answered, but it is not a CollectShine base station.")

        return data

    async def state(self) -> BaseStationState:
        state = BaseStationState.from_json(await self._request("GET", "voice/state"))

        if state.api_version > SUPPORTED_API_VERSION:
            raise UnsupportedVersion(
                f"This base station speaks version {state.api_version}; this integration "
                f"understands {SUPPORTED_API_VERSION}. Update the integration."
            )

        return state

    async def find(self, query: str, *, act: bool = True, power_on: bool = False) -> FindResult:
        return FindResult.from_json(
            await self._request(
                "POST",
                "voice/find",
                {"query": query, "act": act, "power_on": power_on},
            )
        )

    async def set_lights(self, on: bool) -> None:
        await self._request("POST", "lights/on" if on else "lights/off")

    async def dig(self) -> Record | None:
        """Pick a record at random; the shelf runs a light along the strip and stops on it."""
        return Record.from_json(await self._request("POST", "releases/dig"))

    async def clear_highlight(self, release_id: int) -> None:
        await self._request("POST", f"releases/{release_id}/highlight/off")
