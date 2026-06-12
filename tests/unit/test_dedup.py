from ai_screenshot_platform.common.quality.dedup import ContentHashDedupIndex


def test_content_hash_is_stable_for_same_bytes():
    first = ContentHashDedupIndex.calculate_hash(b"same-image")
    second = ContentHashDedupIndex.calculate_hash(b"same-image")

    assert first == second
    assert len(first) == 64


def test_check_returns_duplicate_of_registered_image_id():
    index = ContentHashDedupIndex()
    content_hash = ContentHashDedupIndex.calculate_hash(b"image")

    assert index.check(content_hash).is_duplicate is False

    index.register(content_hash, image_id="00000001")
    result = index.check(content_hash)

    assert result.is_duplicate is True
    assert result.duplicate_of == "00000001"


def test_register_keeps_first_image_id_for_hash():
    index = ContentHashDedupIndex()
    content_hash = ContentHashDedupIndex.calculate_hash(b"image")

    index.register(content_hash, image_id="00000001")
    index.register(content_hash, image_id="00000002")

    assert index.check(content_hash).duplicate_of == "00000001"
