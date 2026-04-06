"""Review summary: ablation diff を人間がレビューしやすい形に再構成する。

diff_summary の情報量は変えず、観点別に整理した review_summary を追加する層。
"""


def build_review_summary(with_result: dict, without_result: dict, diff: dict) -> dict:
    """Single-domain ablation 結果から review_summary を構築する。"""

    ranking_with = [e["candidate_id"] for e in with_result.get("ranking", [])]
    ranking_without = [e["candidate_id"] for e in without_result.get("ranking", [])]
    ranking_changed = ranking_with != ranking_without

    # Score
    score_deltas = []
    for cid, v in diff.get("score_changes", {}).items():
        w = v.get("with") or 0
        wo = v.get("without") or 0
        score_deltas.append({"candidate_id": cid, "delta": round(w - wo, 4)})

    # Confidence
    conf_deltas = []
    for cid, v in diff.get("confidence_changes", {}).items():
        w = v.get("with") or 0
        wo = v.get("without") or 0
        conf_deltas.append({"candidate_id": cid, "delta": round(w - wo, 4)})

    # Reason
    reason_entries = []
    w_ranking = {e["candidate_id"]: e for e in with_result.get("ranking", [])}
    for cid, axes in diff.get("reason_changes", {}).items():
        catalog_ref = False
        entry_w = w_ranking.get(cid, {})
        for a in entry_w.get("axis_scores", []):
            if a["axis"] in axes and "catalog" in a.get("reason", "").lower():
                catalog_ref = True
                break
        reason_entries.append({
            "candidate_id": cid,
            "axes": axes,
            "catalog_reference_added": catalog_ref,
        })

    # Unknown
    unknown_reduced = []
    for cid, v in diff.get("unknown_changes", {}).items():
        w = v.get("with", 0)
        wo = v.get("without", 0)
        if w < wo:
            unknown_reduced.append(cid)
    unknown_unchanged = len(unknown_reduced) == 0

    # Disqualified
    disq_changed = []
    w_map = {e["candidate_id"]: e for e in with_result.get("ranking", [])}
    wo_map = {e["candidate_id"]: e for e in without_result.get("ranking", [])}
    for cid in set(w_map) | set(wo_map):
        dw = w_map.get(cid, {}).get("disqualified")
        dwo = wo_map.get(cid, {}).get("disqualified")
        if dw != dwo:
            disq_changed.append({"candidate_id": cid, "with": dw, "without": dwo})

    return {
        "ranking": {
            "changed": ranking_changed,
            "note": "ranking changed" if ranking_changed else "ranking unchanged",
        },
        "score": {
            "changed_candidates": score_deltas,
        },
        "confidence": {
            "changed_candidates": conf_deltas,
        },
        "reason": {
            "changed_candidates": reason_entries,
        },
        "unknown": {
            "reduced_candidates": unknown_reduced,
            "unchanged": unknown_unchanged,
            "note": "catalog does not resolve unknowns" if unknown_unchanged else "some unknowns reduced",
        },
        "disqualified": {
            "changed_candidates": disq_changed,
        },
    }


def build_cross_domain_review_summary(runs: list[dict]) -> dict:
    """Multi-domain ablation 結果から cross-domain review summary を構築する。"""
    ranking_changed = []
    reason_changed = []
    score_changed = []
    confidence_changed = []
    unknown_reduced = []
    disqualified_changed = []

    for run in runs:
        domain = run["domain"]
        rs = run.get("review_summary", {})

        if rs.get("ranking", {}).get("changed"):
            ranking_changed.append(domain)
        if rs.get("reason", {}).get("changed_candidates"):
            reason_changed.append(domain)
        if rs.get("score", {}).get("changed_candidates"):
            score_changed.append(domain)
        if rs.get("confidence", {}).get("changed_candidates"):
            confidence_changed.append(domain)
        if rs.get("unknown", {}).get("reduced_candidates"):
            unknown_reduced.append(domain)
        if rs.get("disqualified", {}).get("changed_candidates"):
            disqualified_changed.append(domain)

    return {
        "ranking_changed_domains": ranking_changed,
        "reason_changed_domains": reason_changed,
        "score_changed_domains": score_changed,
        "confidence_changed_domains": confidence_changed,
        "unknown_reduced_domains": unknown_reduced,
        "disqualified_changed_domains": disqualified_changed,
        "interpretation_notes": [
            "ranking unchanged is normal",
            "reason changes are still meaningful",
            "catalog should not reduce unknown by itself",
        ],
    }


def format_review_summary_text(rs: dict, query: str = "", model: str = "") -> str:
    """Review summary を人間向けテキストに整形する。"""
    lines = ["=== Live Ablation Review Summary ==="]
    if query:
        lines.append(f"Query: {query}")
    if model:
        lines.append(f"Model: {model}")
    lines.append("")

    # Ranking
    r = rs.get("ranking", {})
    lines.append(f"Ranking: {'changed' if r.get('changed') else 'unchanged'}")
    lines.append("")

    # Score
    sc = rs.get("score", {}).get("changed_candidates", [])
    if sc:
        lines.append("Score changes:")
        for c in sc:
            sign = "+" if c["delta"] >= 0 else ""
            lines.append(f"  {c['candidate_id']}: {sign}{c['delta']:.4f}")
    else:
        lines.append("Score changes: none")
    lines.append("")

    # Confidence
    cc = rs.get("confidence", {}).get("changed_candidates", [])
    if cc:
        lines.append("Confidence changes:")
        for c in cc:
            sign = "+" if c["delta"] >= 0 else ""
            lines.append(f"  {c['candidate_id']}: {sign}{c['delta']:.4f}")
    else:
        lines.append("Confidence changes: none")
    lines.append("")

    # Reason
    rc = rs.get("reason", {}).get("changed_candidates", [])
    if rc:
        lines.append("Reason changes:")
        for c in rc:
            cat_tag = " [+catalog]" if c.get("catalog_reference_added") else ""
            lines.append(f"  {c['candidate_id']}: {', '.join(c['axes'])}{cat_tag}")
    else:
        lines.append("Reason changes: none")
    lines.append("")

    # Unknown
    unk = rs.get("unknown", {})
    if unk.get("unchanged"):
        lines.append("Unknown: unchanged")
    else:
        lines.append(f"Unknown reduced: {', '.join(unk.get('reduced_candidates', []))}")
    lines.append("")

    # Disqualified
    dq = rs.get("disqualified", {}).get("changed_candidates", [])
    if dq:
        lines.append("Disqualified changes:")
        for c in dq:
            lines.append(f"  {c['candidate_id']}: {c['without']} → {c['with']}")
    else:
        lines.append("Disqualified: unchanged")

    return "\n".join(lines)
