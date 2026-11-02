"""Semantic classification of the channels of a SIMPATI acquisition.

The structural parser keeps every channel. This module recognizes the
thermal signals that can be represented, using extendable profiles of
channel aliases. Each acquisition represents only the thermal channels it
really contains; channels that no profile recognizes are kept as
unclassified (``role is None``) and are still available as advanced
channels.

SIMPATI channel names have a type prefix:

- ``A:`` actual value
- ``N:`` nominal value (setpoint)
- ``-.Lm:`` / ``+.Lm:`` lower / upper limit
- ``C:`` counter
- no prefix: digital channel
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .models import TIMESTAMP_COLUMN, SimpatiChannel, SimpatiFormatError

KIND_ACTUAL = "actual"
KIND_SETPOINT = "setpoint"
KIND_LOWER_LIMIT = "lower_limit"
KIND_UPPER_LIMIT = "upper_limit"
KIND_COUNTER = "counter"
KIND_DIGITAL = "digital"
KIND_OTHER = "other"

_PREFIX_KINDS = {
    "a": KIND_ACTUAL,
    "n": KIND_SETPOINT,
    "c": KIND_COUNTER,
    "-.lm": KIND_LOWER_LIMIT,
    "+.lm": KIND_UPPER_LIMIT,
}

_PREFIX_PATTERN = re.compile(r"^\s*([AaNnCc]|[-+]\.[Ll][Mm])\s*:\s*(.*)$")
_COLUMN_PATTERN = re.compile(r"^(?P<name>.*?)(?: \[(?P<unit>[^\[\]]*)\])?$")
_DUPLICATE_SUFFIX = re.compile(r"_\d+$")

#: Units accepted for a thermal channel (compared case-insensitively).
TEMPERATURE_UNITS = frozenset({"°c", "ºc", "degc", "°f", "ºf", "degf"})


@dataclass(frozen=True)
class ChannelProfile:
    """Thermal signal recognized through a list of name aliases.

    ``aliases`` are compared with the channel base name reduced to lower
    case letters and digits (``"Temp. Basket"`` -> ``"tempbasket"``). A
    name matches when it starts with an alias; SIMPATI truncates long
    names, so a truncated name also matches the start of an alias.
    """

    role: str
    label: str
    kind: str
    aliases: tuple[str, ...]
    exact: bool = False

    def matches(self, kind: str, key: str) -> bool:
        if kind != self.kind or not key:
            return False
        for alias in self.aliases:
            if self.exact:
                if key == alias:
                    return True
            elif key.startswith(alias) or (
                len(key) >= 8 and alias.startswith(key)
            ):
                return True
        return False


_CHAMBER = ("temperature", "temperatur", "temperatura", "temp", "chambertemp", "chambertemperature")
_SUPPLY_AIR = ("tsupplyair", "supplyair", "tempsupplyair", "tzuluft", "zuluft", "timpulsion", "aireimpulsion", "tempimpulsion")
_RETURN_AIR = ("treturnair", "returnair", "tempreturnair", "tabluft", "abluft", "tretorno", "aireretorno", "tempretorno")
_BASKET = ("tempcanast", "tempcanasta", "tempcesta", "tempbasket", "baskettemp", "tempkorb")
_HOT_CHAMBER = ("camcalient", "camaracaliente", "hotchamber", "warmchamber", "warmkammer")
_COLD_CHAMBER = ("camfria", "camarafria", "coldchamber", "kaltkammer")
_SPECIMEN = ("tempspecim", "specimen", "tempprobeta", "probeta", "tempmuestra", "temppruefl", "tempprüfl", "prüfling", "pruefling", "tempdut")

#: Profiles in display order. Add a profile or an alias to support more
#: chamber configurations; the order also decides the legend order.
CHANNEL_PROFILES: tuple[ChannelProfile, ...] = (
    ChannelProfile("chamber_temperature", "Chamber temperature", KIND_ACTUAL, _CHAMBER, exact=True),
    ChannelProfile("chamber_setpoint", "Chamber setpoint", KIND_SETPOINT, _CHAMBER, exact=True),
    ChannelProfile("supply_air_temperature", "Supply air temperature", KIND_ACTUAL, _SUPPLY_AIR),
    ChannelProfile("return_air_temperature", "Return air temperature", KIND_ACTUAL, _RETURN_AIR),
    ChannelProfile("basket_temperature", "Basket temperature", KIND_ACTUAL, _BASKET),
    ChannelProfile("basket_setpoint", "Basket setpoint", KIND_SETPOINT, _BASKET),
    ChannelProfile("hot_chamber_temperature", "Hot chamber temperature", KIND_ACTUAL, _HOT_CHAMBER),
    ChannelProfile("hot_chamber_setpoint", "Hot chamber setpoint", KIND_SETPOINT, _HOT_CHAMBER),
    ChannelProfile("cold_chamber_temperature", "Cold chamber temperature", KIND_ACTUAL, _COLD_CHAMBER),
    ChannelProfile("cold_chamber_setpoint", "Cold chamber setpoint", KIND_SETPOINT, _COLD_CHAMBER),
    ChannelProfile("specimen_temperature", "Specimen temperature", KIND_ACTUAL, _SPECIMEN),
)

_PROFILE_ORDER = {profile.role: order for order, profile in enumerate(CHANNEL_PROFILES)}


def split_column_name(column: str) -> tuple[str, str]:
    """``"A:Temp canast [°C]"`` -> ``("A:Temp canast", "°C")``."""
    match = _COLUMN_PATTERN.match(column)
    if match is None:
        return column, ""
    return match.group("name"), match.group("unit") or ""


def channel_kind(name: str) -> tuple[str, str]:
    """Return the channel kind and its base name without prefix."""
    base = _DUPLICATE_SUFFIX.sub("", name)
    match = _PREFIX_PATTERN.match(base)
    if match is None:
        return KIND_DIGITAL if base else KIND_OTHER, base.strip()
    prefix = match.group(1).casefold()
    return _PREFIX_KINDS.get(prefix, KIND_OTHER), match.group(2).strip()


def alias_key(base_name: str) -> str:
    """Reduce a name to lower case letters and digits for alias matching."""
    normalized = unicodedata.normalize("NFC", base_name).casefold()
    return "".join(character for character in normalized if character.isalnum())


def is_temperature_unit(unit: str) -> bool:
    return unit.replace(" ", "").casefold() in TEMPERATURE_UNITS


def _match_profile(kind: str, base_name: str, unit: str) -> ChannelProfile | None:
    if not is_temperature_unit(unit):
        return None
    key = alias_key(base_name)
    for profile in CHANNEL_PROFILES:
        if profile.matches(kind, key):
            return profile
    return None


def classify_channels(dataframe: pd.DataFrame) -> list[SimpatiChannel]:
    """Classify every channel of a parsed acquisition, in column order.

    A channel is thermal (representable) when a profile recognizes it, its
    unit is a temperature and it contains at least one numeric value.
    Repeated roles are numbered (``Specimen temperature 2``).
    """
    channels: list[SimpatiChannel] = []
    role_counts: dict[str, int] = {}

    for column in dataframe.columns:
        column = str(column)
        if column == TIMESTAMP_COLUMN:
            continue
        name, unit = split_column_name(column)
        kind, base_name = channel_kind(name)
        has_data = bool(dataframe[column].notna().any())
        profile = _match_profile(kind, base_name, unit)

        role = label = None
        if profile is not None:
            role_counts[profile.role] = role_counts.get(profile.role, 0) + 1
            count = role_counts[profile.role]
            role = profile.role
            label = profile.label if count == 1 else f"{profile.label} {count}"

        channels.append(
            SimpatiChannel(
                column=column,
                name=name,
                unit=unit,
                kind=kind,
                base_name=base_name,
                role=role,
                label=label,
                thermal=role is not None and has_data,
                has_data=has_data,
            )
        )
    return channels


def thermal_channels(channels: Iterable[SimpatiChannel]) -> list[SimpatiChannel]:
    """Representable thermal channels in profile (legend) order."""
    indexed = [
        (position, channel)
        for position, channel in enumerate(channels)
        if channel.thermal
    ]
    indexed.sort(key=lambda item: (_PROFILE_ORDER.get(item[1].role or "", 99), item[0]))
    return [channel for _, channel in indexed]


def get_temperature_channels(dataframe: pd.DataFrame) -> dict[str, str]:
    """Return ``{label: column}`` for the representable thermal channels.

    Raises:
        SimpatiFormatError: when the acquisition has no thermal channel.
    """
    mapping = {
        channel.display_label: channel.column
        for channel in thermal_channels(classify_channels(dataframe))
    }
    if not mapping:
        raise SimpatiFormatError("No representable temperature channels were found.")
    return mapping
