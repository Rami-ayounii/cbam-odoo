from scoring import aggregate_field_scores, score_record


def test_score_record_matches_identical_values():
    ground_truth = {"quantity_tonnes": 100.0, "data_source": "actual", "direct_emissions_actual": 1.9}
    written = {"quantity_tonnes": 100.0, "data_source": "actual", "direct_emissions_actual": 1.9}

    scores = score_record(ground_truth, written)

    assert scores["quantity_tonnes"] is True
    assert scores["data_source"] is True
    assert scores["direct_emissions_actual"] is True


def test_score_record_flags_mismatched_values():
    ground_truth = {"quantity_tonnes": 100.0, "data_source": "actual"}
    written = {"quantity_tonnes": 99.0, "data_source": "default"}

    scores = score_record(ground_truth, written)

    assert scores["quantity_tonnes"] is False
    assert scores["data_source"] is False


def test_score_record_float_comparison_tolerates_rounding():
    ground_truth = {"quantity_tonnes": 100.0}
    written = {"quantity_tonnes": 100.0000001}

    scores = score_record(ground_truth, written)

    assert scores["quantity_tonnes"] is True


def test_score_record_missing_field_in_written_is_a_miss():
    ground_truth = {"quantity_tonnes": 100.0}
    written = {}

    scores = score_record(ground_truth, written)

    assert scores["quantity_tonnes"] is False


def test_score_record_none_ground_truth_field_is_skipped_not_scored():
    # direct_emissions_actual is null in ground truth for "default"-sourced
    # synthetic records - nothing to score against.
    ground_truth = {"direct_emissions_actual": None}
    written = {"direct_emissions_actual": None}

    scores = score_record(ground_truth, written)

    assert "direct_emissions_actual" not in scores


def test_aggregate_field_scores_computes_accuracy_per_field():
    per_record_scores = [
        {"quantity_tonnes": True, "data_source": True},
        {"quantity_tonnes": False, "data_source": True},
        {"quantity_tonnes": True},  # data_source wasn't scored for this record
    ]

    aggregated = aggregate_field_scores(per_record_scores)

    assert aggregated["quantity_tonnes"] == {"correct": 2, "total": 3, "accuracy": 2 / 3}
    assert aggregated["data_source"] == {"correct": 2, "total": 2, "accuracy": 1.0}
