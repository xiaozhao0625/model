from ai_screenshot_platform.v3.model.manifest import validate_model_manifest


def test_model_manifest_requires_provider_keys():
    assert validate_model_manifest({"providers": [{"name": "showui"}]})
    assert validate_model_manifest(
        {
            "providers": [
                {
                    "name": "showui",
                    "type": "ui_model",
                    "path": "models/showui",
                    "enabled": False,
                    "sha256_required": True,
                }
            ]
        }
    ) == []
