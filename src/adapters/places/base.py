"""Place adapter interfaces."""

from typing import Protocol


class PlaceSearcher(Protocol):
    """候補検索 adapter の interface。"""

    def search_places(
        self, conditions: dict, *, enable_fallback: bool = True,
    ) -> dict:
        """検索条件から候補を返す。

        Returns:
            {
                "results": [{"source", "source_id", "title", "snippet"}, ...],
                "search_diagnostics": {...},
            }
        """
        ...


class PlaceRetriever(Protocol):
    """候補詳細取得 adapter の interface。"""

    def retrieve_place(self, source: str, source_id: str) -> dict:
        """source_id に対応する詳細レコードを返す。

        Returns:
            {
                "source": str,
                "source_id": str,
                "raw_record": {...},
            }
        """
        ...
