"""Solution Catalog loader.

candidate_id → Solution Catalog entry の lookup を提供する。
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_CATALOG_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "examples"
    / "restaurant_solution_catalog.json"
)


def load_solution_catalog(path: str | Path | None = None) -> dict[str, dict]:
    """Solution Catalog JSON を読み込み、candidate_id をキーとした dict を返す。

    Args:
        path: catalog JSON のパス。None ならデフォルトの restaurant sample を使用。

    Returns:
        {candidate_id: catalog_entry, ...}
    """
    catalog_path = Path(path) if path else _DEFAULT_CATALOG_PATH
    if not catalog_path.exists():
        logger.warning("Solution catalog not found: %s", catalog_path)
        return {}

    entries = json.loads(catalog_path.read_text("utf-8"))
    catalog = {entry["candidate_id"]: entry for entry in entries}
    logger.info("Loaded solution catalog: %d entries from %s",
                len(catalog), catalog_path.name)
    return catalog


def get_catalog_entry(
    catalog: dict[str, dict],
    candidate_id: str,
) -> dict | None:
    """candidate_id に対応する catalog entry を返す。無ければ None。"""
    return catalog.get(candidate_id)
