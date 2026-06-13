from __future__ import annotations

from ai_screenshot_platform.workers.android.emulator_profile import AndroidEmulatorProfile, AndroidEmulatorProfileLoader


def test_android_emulator_profile_defaults_to_generic_adb(tmp_path):
    profile = AndroidEmulatorProfile(profile_id="dev", app_package="pkg", app_activity="Main")
    path = tmp_path / "profiles.json"
    path.write_text('{"profiles":[{"profile_id":"dev","app_package":"pkg","app_activity":"Main"}]}', encoding="utf-8")

    loaded = AndroidEmulatorProfileLoader(path).load()[0]

    assert profile.emulator_type == "generic_adb"
    assert loaded.profile_id == "dev"
