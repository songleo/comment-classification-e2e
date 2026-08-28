from comment_classifier.data_validation import EXPECTED_LABEL_COUNTS, validate


def test_checked_in_dataset_is_valid() -> None:
    summary = validate()
    assert set(summary) == {"train", "validation", "test"}
    assert all(set(counts) == {"positive", "negative", "neutral", "complaint"} for counts in summary.values())
    assert summary == {
        split: {
            "complaint": expected_count,
            "negative": expected_count,
            "neutral": expected_count,
            "positive": expected_count,
        }
        for split, expected_count in EXPECTED_LABEL_COUNTS.items()
    }
