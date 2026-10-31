"""Collect module failures while allowing the remaining tests to run."""

from std.sys import is_defined

# Module entry points use an unused compile-time parameter so that
# __functions_in_module() excludes the entry point from its own discovery.


def module_selected[name: StaticString]() -> Bool:
    """Select a module using optional STDEXT_TEST_* compile-time defines."""
    return (
        not is_defined["STDEXT_TEST_FILTERED"]()
        or is_defined["STDEXT_TEST_" + name]()
    )


struct TestRunner(
    Deinitable where (False, "Call tests^.finish() to report all test results")
):
    """Run module entry points and report failures after all modules finish."""

    var modules: Int
    var failures: Int

    def __init__(out self):
        """Create an empty runner."""
        self.modules = 0
        self.failures = 0

    def run[Fn: def() raises -> None](mut self, name: String, test: Fn):
        """Run a module, recording its failure without stopping later modules.
        """
        self.modules += 1
        print("\nRunning:", name)
        try:
            test()
        except error:
            self.failures += 1
            print("FAIL:", name, error)

    def finish(deinit self) raises:
        """Consume the runner and raise if any module failed or none ran."""
        print("\nRan", self.modules, "test modules;", self.failures, "failed.")
        if self.modules == 0:
            raise Error("No Mojo test modules selected")
        if self.failures > 0:
            raise Error("Mojo tests failed")
