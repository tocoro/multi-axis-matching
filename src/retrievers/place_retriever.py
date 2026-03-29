"""Backward-compatible wrapper. Logic moved to src.adapters.places.mock_places."""

from src.adapters.places.mock_places import MockPlaceRetriever

_default = MockPlaceRetriever()


def retrieve_place(source: str, source_id: str) -> dict:
    return _default.retrieve_place(source, source_id)
