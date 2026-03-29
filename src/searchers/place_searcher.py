"""Backward-compatible wrapper. Logic moved to src.adapters.places.mock_places."""

from src.adapters.places.mock_places import MockPlaceSearcher

_default = MockPlaceSearcher()


def search_places(conditions: dict, *, enable_fallback: bool = True) -> dict:
    return _default.search_places(conditions, enable_fallback=enable_fallback)
