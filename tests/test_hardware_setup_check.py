import sys
from pathlib import Path

import scripts.check_hardware_setup as check


def test_meadowlark_sdk_check_reports_required_files(tmp_path):
    sdk_dir = tmp_path / "SDK"
    sdk_dir.mkdir()
    (sdk_dir / "Blink_C_wrapper.dll").write_text("", encoding="utf-8")

    results = check.check_meadowlark_sdk(sdk_dir)
    by_name = {result.name: result for result in results}

    assert by_name["Meadowlark SDK directory"].ok is True
    assert by_name["Meadowlark Blink_C_wrapper.dll"].ok is True
    assert by_name["Meadowlark HdmiDisplay.dll"].ok is False


def test_python_check_returns_structured_result():
    result = check.check_python()

    assert result.name == "Python"
    assert str(sys.version_info.major) in result.detail
