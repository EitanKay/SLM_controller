from __future__ import annotations

import importlib
import platform
import struct
import sys
from dataclasses import dataclass
from pathlib import Path


MEADOWLARK_SDK_DIR = Path(r"C:\Program Files\Meadowlark Optics\Blink DVI\SDK")
MEADOWLARK_REQUIRED_FILES = (
    "Blink_C_wrapper.dll",
    "HdmiDisplay.dll",
    "ImageGen.dll",
    "freeglut.dll",
    "glew64.dll",
)
REQUIRED_IMPORTS = (
    "numpy",
    "PIL",
    "scipy",
    "matplotlib",
    "PyQt6",
    "slmsuite",
    "pylablib",
    "tqdm",
)
REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_LUT_DIR = REPO_ROOT / "slm-files" / "LUT_files"
REPO_WFC_DIR = REPO_ROOT / "slm-files" / "WFC_files"


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def check_python() -> CheckResult:
    version = platform.python_version()
    arch = struct.calcsize("P") * 8
    ok = sys.version_info[:2] == (3, 12) and arch == 64
    detail = f"Python {version}, {arch}-bit"
    if not ok:
        detail += " (expected Python 3.12 x64)"
    return CheckResult("Python", ok, detail)


def check_imports() -> list[CheckResult]:
    results: list[CheckResult] = []
    for module_name in REQUIRED_IMPORTS:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            results.append(CheckResult(f"Import {module_name}", False, str(exc)))
        else:
            results.append(CheckResult(f"Import {module_name}", True, "available"))
    return results


def check_meadowlark_sdk(sdk_dir: Path = MEADOWLARK_SDK_DIR) -> list[CheckResult]:
    results = [
        CheckResult(
            "Meadowlark SDK directory",
            sdk_dir.exists(),
            str(sdk_dir),
        )
    ]
    for filename in MEADOWLARK_REQUIRED_FILES:
        path = sdk_dir / filename
        results.append(CheckResult(f"Meadowlark {filename}", path.exists(), str(path)))
    return results


def check_calibration_files() -> list[CheckResult]:
    lut_files = sorted(REPO_LUT_DIR.glob("*.lut")) if REPO_LUT_DIR.exists() else []
    wfc_files = sorted(REPO_WFC_DIR.glob("*.bmp")) if REPO_WFC_DIR.exists() else []
    return [
        CheckResult(
            "Repo LUT files",
            bool(lut_files),
            f"{len(lut_files)} .lut file(s) in {REPO_LUT_DIR}",
        ),
        CheckResult(
            "Repo WFC files",
            bool(wfc_files),
            f"{len(wfc_files)} .bmp file(s) in {REPO_WFC_DIR}",
        ),
    ]


def check_thorlabs() -> CheckResult:
    try:
        import pylablib as pll
        from pylablib.devices import Thorlabs
    except Exception as exc:
        return CheckResult("Thorlabs pylablib", False, f"import failed: {exc}")

    dll_path = pll.par.get("devices/dlls/thorlabs_tlcam", None)
    try:
        cameras = Thorlabs.list_cameras_tlcam()
    except Exception as exc:
        detail = f"pylablib available; camera query failed: {exc}"
        if dll_path:
            detail += f"; configured DLL path: {dll_path}"
        return CheckResult("Thorlabs camera query", False, detail)

    return CheckResult(
        "Thorlabs camera query",
        bool(cameras),
        f"{len(cameras)} camera(s) found: {cameras}",
    )


def run_checks() -> list[CheckResult]:
    return [
        check_python(),
        *check_imports(),
        *check_meadowlark_sdk(),
        *check_calibration_files(),
        check_thorlabs(),
    ]


def main() -> int:
    results = run_checks()
    for result in results:
        status = "OK" if result.ok else "WARN"
        print(f"[{status}] {result.name}: {result.detail}")

    required = [
        result
        for result in results
        if result.name == "Python"
        or result.name.startswith("Import ")
        or result.name.startswith("Meadowlark ")
        or result.name == "Meadowlark SDK directory"
    ]
    return 0 if all(result.ok for result in required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
