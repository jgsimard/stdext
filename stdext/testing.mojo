"""Test discovery and failure aggregation for independent Mojo projects."""

from std.reflection import call_location
from std.testing import TestSuite
from .test_runner import TestRunner, module_selected


@inline(.always)
def run_module[functions: Tuple]() raises:
    """Discover and run test_* functions, rejecting an empty test module.

    Call this from a module entry point with __functions_in_module(). Keep the
    entry point parametric so reflection excludes it from its own discovery.
    Assertions and individual test reporting come from std.testing.
    """
    var suite = TestSuite.discover_tests[functions](location=call_location())
    if len(suite.tests) == 0:
        suite^.abandon()
        raise Error("No Mojo tests discovered in module")
    suite^.run()
