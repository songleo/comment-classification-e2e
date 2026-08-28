from comment_classifier.data_validation import validate


def test_checked_in_dataset_is_valid() -> None:
    summary = validate()
    assert set(summary) == {"train", "validation", "test"}
    assert all(set(counts) == {"positive", "negative", "neutral", "complaint"} for counts in summary.values())
