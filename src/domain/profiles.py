"""DomainProfile / ProblemTypeSpec: ドメインごとの基本情報を表す最小構造。

example_axes は LLM の axis selection を制約するものではなく、
ドメインの想定軸を説明するための profile 情報。
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProblemTypeSpec:
    """問題タイプの最小情報。"""
    problem_type: str
    risk_level: str  # "normal" or "high"
    example_axes: list[str] = field(default_factory=list)
    description: str = ""


@dataclass(frozen=True)
class DomainProfile:
    """ドメインの基本情報。"""
    domain_name: str
    default_problem_type: ProblemTypeSpec
    candidate_source_kind: str
    normalizer_name: str
    search_adapter_name: str = ""
    retriever_name: str = ""
    supports_solution_catalog: bool = False
    description: str = ""


# ---------------------------------------------------------------------------
# Registered profiles
# ---------------------------------------------------------------------------

RESTAURANT_PROBLEM = ProblemTypeSpec(
    problem_type="local.restaurant",
    risk_level="normal",
    example_axes=["cuisine", "budget", "atmosphere", "location", "rating"],
    description="Restaurant search and evaluation",
)

CLINIC_PROBLEM = ProblemTypeSpec(
    problem_type="local.clinic",
    risk_level="high",
    example_axes=["specialty_fit", "distance", "hours", "insurance", "availability"],
    description="Medical clinic search (high-risk domain)",
)

RESTAURANT_PROFILE = DomainProfile(
    domain_name="restaurant",
    default_problem_type=RESTAURANT_PROBLEM,
    candidate_source_kind="places",
    normalizer_name="restaurant_normalizer",
    search_adapter_name="MockPlaceSearcher",
    retriever_name="MockPlaceRetriever",
    supports_solution_catalog=True,
    description="Restaurant matching with Google Places integration",
)

CLINIC_PROFILE = DomainProfile(
    domain_name="clinic",
    default_problem_type=CLINIC_PROBLEM,
    candidate_source_kind="clinic_mock",
    normalizer_name="clinic_normalizer",
    search_adapter_name="MockClinicSearcher",
    retriever_name="MockClinicRetriever",
    supports_solution_catalog=False,
    description="Clinic matching (mock-only, demo)",
)

DOMAIN_PROFILES: dict[str, DomainProfile] = {
    "restaurant": RESTAURANT_PROFILE,
    "clinic": CLINIC_PROFILE,
}


def get_domain_profile(name: str) -> DomainProfile | None:
    """ドメイン名から profile を取得する。未登録なら None。"""
    return DOMAIN_PROFILES.get(name)
