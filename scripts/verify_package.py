import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

def _has_build_backend() -> bool:
    try:
        import setuptools.build_meta  # noqa: F401
    except ImportError:
        return False
    return True

def main() -> None:
    try:
        with tempfile.TemporaryDirectory(prefix="pritset-python-package-") as directory:
            output = Path(directory)
            build_environment = dict(os.environ)
            build_environment["PIP_NO_CACHE_DIR"] = "1"
            command = [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                ".",
                "--no-deps",
                "--wheel-dir",
                str(output),
            ]
            if _has_build_backend():
                command.insert(-2, "--no-build-isolation")
            subprocess.run(
                command,
                cwd=ROOT,
                env=build_environment,
                check=True,
            )    
            
            wheels = list(output.glob("pritset-0.1.5-*.whl"))
            if len(wheels) != 1:
                raise RuntimeError("Expected exactly one pritset 0.1.5 wheel.")
            wheel = wheels[0]
            with zipfile.ZipFile(wheel) as archive:
                names = set(archive.namelist())
            required_suffixes = (
                "pritset/__init__.py",
                "pritset/py.typed",
                "share/pritset/contract/openapi.yaml",
                "share/pritset/contract/contract.lock.json",
            )
            for suffix in required_suffixes:
                if not any(name.endswith(suffix) for name in names):
                    raise RuntimeError("Built wheel is missing %s." % suffix)

            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(wheel)
            subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from pritset import AsyncPritsetClient, PritsetClient; "
                    "assert PritsetClient.__name__ == 'PritsetClient'; "
                    "assert AsyncPritsetClient.__name__ == 'AsyncPritsetClient'",
                ],
                cwd=output,
                env=environment,
                check=True,
            )
            print("Wheel contents and clean import verified: %s" % wheel.name)
    finally:
        for generated in (ROOT / "build", ROOT / "src" / "pritset.egg-info"):
            shutil.rmtree(generated, ignore_errors=True)


if __name__ == "__main__":
    main()
