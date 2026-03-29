"""Google Places adapter の設定。"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class GooglePlacesConfig:
    api_key: str = ""
    timeout_seconds: int = 10
    max_results: int = 10
    use_new_api: bool = True  # Places API (New) を使用

    @classmethod
    def from_env(cls) -> "GooglePlacesConfig":
        return cls(
            api_key=os.environ.get("GOOGLE_PLACES_API_KEY", ""),
            timeout_seconds=int(os.environ.get("GOOGLE_PLACES_TIMEOUT_SECONDS", "10")),
            max_results=int(os.environ.get("GOOGLE_PLACES_MAX_RESULTS", "10")),
            use_new_api=os.environ.get("GOOGLE_PLACES_USE_NEW_API", "true").lower() == "true",
        )
