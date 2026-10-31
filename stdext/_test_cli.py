"""Discover project tests and generate temporary Mojo suite entry points.

Run from any project with ``python /path/to/stdext/stdext/_test_cli.py`` or,
after installing the Pixi package, ``stdext-test``. Uses only Python's stdlib.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


_IGNORED_DIRS = {"__pycache__", "__mojocache__", "build", "dist"}
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")


def discover(root: Path, paths: list[str]) -> list[Path]:
    """Collect sorted, unique test files and reject invalid explicit paths."""
    selected: set[Path] = set()
    for value in paths:
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            raise ValueError(f"Test path does not exist: {value}")
        if path.is_file():
            candidates = [path]
        else:
            candidates = []
            for directory, dirs, files in os.walk(path):
                dirs[:] = sorted(
                    d for d in dirs if not d.startswith(".") and d not in _IGNORED_DIRS
                )
                candidates.extend(Path(directory) / name for name in files)
        matches = 0
        for candidate in candidates:
            if not candidate.name.startswith("test_") or candidate.suffix not in {".mojo", ".py"}:
                continue
            resolved = candidate.resolve()
            if not resolved.is_relative_to(root):
                raise ValueError(f"Test file is outside project root {root}: {candidate}")
            if resolved.suffix == ".mojo":
                parts = resolved.relative_to(root).with_suffix("").parts
                if not all(_IDENTIFIER.fullmatch(part) for part in parts):
                    raise ValueError(f"Mojo test path must contain valid module identifiers: {candidate}")
            selected.add(resolved)
            matches += 1
        if not matches:
            raise ValueError(f"No test_*.mojo or test_*.py files found in: {value}")
    return sorted(selected)


def group_key(relative: Path) -> str:
    """Use one compilation per subsystem, as in Bajo's original runner."""
    parents = relative.parts[:-1]
    if not parents:
        return "."
    count = 2 if parents[0] in {"test", "tests"} else 1
    return "/".join(parents[:count])


def runner_source(root: Path, files: list[Path]) -> str:
    """Import only selected files; unselected GPU modules are never compiled."""
    lines = ["from stdext.testing import TestRunner", ""]
    for index, file in enumerate(files):
        module = ".".join(file.relative_to(root).with_suffix("").parts)
        lines.append(f"import {module} as _stdext_module_{index}")
    lines.extend(["", "", "def main() raises:", "    var tests = TestRunner()"])
    for index, file in enumerate(files):
        name = json.dumps(file.relative_to(root).as_posix())
        lines.append(f"    tests.run({name}, _stdext_module_{index}.run_tests[True])")
    lines.append("    tests^.finish()")
    return "\n".join(lines) + "\n"


def run(command: list[str], root: Path) -> bool:
    try:
        return subprocess.run(command, cwd=root, check=False).returncode == 0
    except OSError as error:
        print(f"Could not run {command[0]}: {error}", file=sys.stderr, flush=True)
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="test files or directories (default: test/ or tests/)")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project and import root (default: current directory)")
    parser.add_argument("--list", action="store_true", help="list selected files without compiling or running")
    parser.add_argument("-I", "--include", action="append", default=[], help="additional Mojo import directory")
    parser.add_argument("-D", "--define", action="append", default=[], help="Mojo compile-time KEY=VALUE")
    parser.add_argument("--mojo", default="mojo", help="Mojo compiler executable")
    parser.add_argument("--mojo-arg", action="append", default=[], help="extra compiler argument; use --mojo-arg=--flag")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"Project root is not a directory: {root}")
    paths = args.paths or ["test" if (root / "test").is_dir() else "tests"]
    try:
        files = discover(root, paths)
    except ValueError as error:
        parser.error(str(error))
    if args.list:
        for file in files:
            print(file.relative_to(root).as_posix())
        return 0

    groups: dict[str, list[Path]] = {}
    python_files: list[Path] = []
    for file in files:
        if file.suffix == ".mojo":
            groups.setdefault(group_key(file.relative_to(root)), []).append(file)
        else:
            python_files.append(file)

    # This works both in a checkout and in $PREFIX/lib/mojo/stdext/.
    library_root = Path(__file__).resolve().parent.parent
    flags = ["-I", str(library_root), "-I", str(root)]
    for directory in args.include:
        flags.extend(["-I", str((root / directory).resolve())])
    for define in args.define:
        flags.extend(["-D", define])
    flags.extend(args.mojo_arg)

    failures = 0
    with tempfile.TemporaryDirectory(prefix="stdext-tests-") as directory:
        runner = Path(directory) / "_stdext_runner.mojo"
        for group, modules in groups.items():
            print(f"Running Mojo tests in: {group}", flush=True)
            runner.write_text(runner_source(root, modules), encoding="utf-8")
            if not run([args.mojo, "run", *flags, str(runner)], root):
                failures += 1
    for file in python_files:
        print(f"Running: {file.relative_to(root).as_posix()}", flush=True)
        if not run([sys.executable, str(file)], root):
            failures += 1
    print(f"\nRan {len(groups)} Mojo suites and {len(python_files)} Python files; {failures} failed.", flush=True)
    return int(failures > 0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
