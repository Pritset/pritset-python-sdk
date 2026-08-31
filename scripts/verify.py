import compileall
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(*arguments: str, env=None) -> None:
    subprocess.run([sys.executable, *arguments], cwd=ROOT, env=env, check=True)


def main() -> None:
    run("scripts/verify_contract.py")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    run("-m", "unittest", "discover", "-s", "tests", "-v", env=environment)
    if not compileall.compile_dir(str(ROOT / "src"), quiet=1):
        raise RuntimeError("Package bytecode compilation failed.")
    if not compileall.compile_dir(str(ROOT / "examples"), quiet=1):
        raise RuntimeError("Example bytecode compilation failed.")
    run("scripts/verify_package.py")


if __name__ == "__main__":
    main()
