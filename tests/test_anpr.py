from src.anpr.preprocess import preprocess_image


def test_preprocess_handles_bytes():
    # Test with dummy image bytes
    dummy_bytes = b"fake-image-data"
    result = preprocess_image(dummy_bytes)
    assert isinstance(result, dict)
    assert result["status"] == "preprocessed"
    assert result["size"] == len(dummy_bytes)
