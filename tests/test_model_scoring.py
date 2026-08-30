from engine.model_scoring import filter_by_min_tier, rank_models

TEST_MODELS = [
    {"id": "cheap-a", "tier": "cheap"},
    {"id": "mid-a", "tier": "mid"},
    {"id": "frontier-a", "tier": "frontier"},
]

WEIGHTS = {"capabilityFit": 0.3, "costEfficiency": 0.3, "latencyFit": 0.25, "deploymentFit": 0.15}


def test_filter_by_min_tier_eliminates_below_minimum():
    result = filter_by_min_tier(TEST_MODELS, "mid")
    assert [m["id"] for m in result] == ["mid-a", "frontier-a"]


def test_filter_by_min_tier_passes_all_when_no_minimum():
    assert len(filter_by_min_tier(TEST_MODELS, None)) == 3


def test_hard_constraint_eliminates_cheap_model_for_complex_use_case():
    """Elimination, not just a low score."""
    result = rank_models(
        models=TEST_MODELS,
        min_model_tier="mid",
        data_sensitivity=None,
        complexity_tier="complex",
        weights=WEIGHTS,
        cost_per_request_by_model_id={"mid-a": 0.01, "frontier-a": 0.05},
    )
    model_ids = [c["model_id"] for c in result["candidates"]]
    assert "cheap-a" not in model_ids


def test_frontier_model_does_not_always_win_once_above_capability_bar():
    result = rank_models(
        models=TEST_MODELS,
        min_model_tier="mid",
        data_sensitivity=None,
        complexity_tier="moderate",  # mid-a exactly meets this bar
        weights=WEIGHTS,
        cost_per_request_by_model_id={"mid-a": 0.01, "frontier-a": 0.05},
    )
    scores = {c["model_id"]: c["score"] for c in result["candidates"]}
    # mid-a exactly meets the capability bar (full credit) and is far
    # cheaper; frontier-a only gets diminished extra credit for being
    # over-qualified, so it should not win here.
    assert scores["mid-a"] > scores["frontier-a"]


def test_empty_candidate_list_when_nothing_meets_tier_constraint():
    result = rank_models(
        models=TEST_MODELS,
        min_model_tier="frontier-extended",
        data_sensitivity=None,
        complexity_tier="complex",
        weights=WEIGHTS,
        cost_per_request_by_model_id={},
    )
    assert result["candidates"] == []
    assert result["note"]
