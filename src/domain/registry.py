"""Adapter registry: ドメインごとの実行時 binding を1か所で管理する。

DomainProfile は説明的メタ情報 (axes 例, risk_level など)。
AdapterBinding は実行時の binding (searcher, retriever, normalizer の参照)。
"""

from dataclasses import dataclass
from typing import Any, Callable

from src.adapters.clinic.mock_clinic import MockClinicRetriever, MockClinicSearcher
from src.adapters.places.mock_places import MockPlaceRetriever, MockPlaceSearcher
from src.normalizers.clinic_normalizer import normalize_clinic
from src.normalizers.restaurant_normalizer import normalize_restaurant


@dataclass(frozen=True)
class AdapterBinding:
    """ドメインの実行時 adapter binding。"""
    domain_name: str
    searcher_factory: Callable[[], Any]
    retriever_factory: Callable[[], Any]
    normalizer_fn: Callable[..., dict]


RESTAURANT_BINDING = AdapterBinding(
    domain_name="restaurant",
    searcher_factory=MockPlaceSearcher,
    retriever_factory=MockPlaceRetriever,
    normalizer_fn=normalize_restaurant,
)

CLINIC_BINDING = AdapterBinding(
    domain_name="clinic",
    searcher_factory=MockClinicSearcher,
    retriever_factory=MockClinicRetriever,
    normalizer_fn=normalize_clinic,
)

ADAPTER_REGISTRY: dict[str, AdapterBinding] = {
    "restaurant": RESTAURANT_BINDING,
    "clinic": CLINIC_BINDING,
}


def get_adapter_binding(domain_name: str) -> AdapterBinding | None:
    """ドメイン名から adapter binding を取得する。未登録なら None。"""
    return ADAPTER_REGISTRY.get(domain_name)
