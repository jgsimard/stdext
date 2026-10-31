# stdext

Small, reusable Mojo utilities until they belong in the standard library or an
established library. Keep additions focused, independent of applications, and
easy to replace when an upstream equivalent arrives.

The first utility is the testing framework extracted from Bajo: stdlib test
discovery and assertions, module failure aggregation, and a launcher that finds
tests automatically. There are no handwritten subsystem runners or test lists
to maintain.

## Use from another project

Add a Pixi path dependency (adjust the path to your stdext checkout):

```toml
[workspace]
channels = ["https://conda.modular.com/max-nightly", "conda-forge"]
platforms = ["linux-64"]
preview = ["pixi-build"]

[dependencies]
stdext = { path = "../stdext" }

[tasks]
test = "stdext-test"
```

The package installs Mojo sources and the `stdext-test` command. Imports such as
`from stdext.testing import TestRunner` work without extra `-I` flags. Source
distribution avoids tying the package to one compiler's precompiled format.
The minimum supported compiler is Mojo `1.3.0.dev2026103105`; the launcher needs
Python 3.11 or later and uses only its standard library.

Create `test/test_example.mojo`:

```mojo
from std.testing import assert_equal
from stdext.testing import run_module


def test_example() raises:
    assert_equal(6 * 7, 42)


def run_tests[_discovery: Bool = True]() raises:
    run_module[__functions_in_module()]()
```

The compile-time parameter keeps `run_tests` out of its own reflection results.
Tests are parameterless `def test_*() raises` functions. Use assertions from
`std.testing`; `run_module` delegates individual test reporting to its
`TestSuite` and rejects modules that discover no tests.

```bash
pixi run test
pixi run test test/core
pixi run test test/core/test_vec.mojo
pixi run test test/core test/parser
pixi run test --list
pixi run test -I src -D MY_TEST_FEATURE=1
pixi run test --mojo-arg=--target-accelerator --mojo-arg=sm_120 test/gpu
```

The launcher defaults to `test/`, falling back to `tests/`. Explicit paths are
relative to the project root, which defaults to the working directory and can
be set with `--root`. It finds `test_*.mojo` and `test_*.py` recursively, sorts
and deduplicates selections, and skips hidden directories and build caches.
Mojo test paths must be valid import paths beneath the project root. Python
files run as scripts with the launcher's Python interpreter, as in Bajo.

Selected Mojo modules compile in one process per subsystem (`test/core`,
`test/parser`, etc.). Only selected files are imported, so selecting CPU tests
does not compile neighboring GPU tests. Module failures, failed compilations,
and Python failures allow later suites to run; the command returns nonzero if
any fail. Missing paths and empty selections also fail. A native crash stops
the current Mojo process; later suites still run.

For a complete dependent project, see [examples/consumer](examples/consumer).
Without installing a package, run from your project's root:

```bash
pixi run python /path/to/stdext/stdext/_test_cli.py test
```

For direct Mojo imports from a checkout, add its root with `mojo run -I
/path/to/stdext ...`.

## Migrate Bajo-style tests

Existing modules exposing `run_tests[_discovery: Bool = True]()` work unchanged,
including modules that directly use `TestSuite.discover_tests`. Replace the
project's shell runner with `stdext-test` and add the dependency above. Existing
handwritten `run_tests.mojo` files are ignored by automatic discovery.

For manually assembled suites, import `TestRunner` and `module_selected` from
`stdext.testing` (the original `stdext.test_runner` import also works). Call
`tests.run("module name", module.run_tests[True])` for each module and always
consume the runner with `tests^.finish()`. Manual compile-time filters use
`STDEXT_TEST_FILTERED` and `STDEXT_TEST_<name>` in place of Bajo's defines.

## Develop

```bash
pixi run test          # Mojo runner tests and launcher integration tests
pixi run test_cli      # launcher tests only
pixi run test_install  # build/install into a temporary external Pixi project
pixi run fmt
pixi build            # build a reusable Conda package
```
