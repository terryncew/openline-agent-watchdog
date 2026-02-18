# Run this as:
#   python -m tests.test_watchdog
#
# This is a simple sanity test that avoids any absolute-path hacks.

from agent_watchdog import AgentWatchdog, WatchdogConfig


def test_freshness_moves_the_right_way():
    wd = AgentWatchdog(WatchdogConfig(freshness_window=8, min_freshness_ratio=0.28))

    fresh = [
        "We should compute the BAO likelihood correctly.",
        "Now check whether DV exists in the dataset.",
        "Patch the observable dispatcher to handle DV explicitly.",
        "Re-run the fit and compare chi^2.",
        "Now compute growth and fσ8 at z=0.5.",
        "Fix the S8 formula to sqrt(Om/0.3).",
    ]

    loopy = [
        "Ship it.",
        "Ship it.",
        "Ship it.",
        "Ship it.",
        "Ship it.",
        "Ship it.",
    ]

    fr_fresh = wd.freshness_ratio(fresh)
    fr_loopy = wd.freshness_ratio(loopy)

    assert fr_fresh > fr_loopy, (fr_fresh, fr_loopy)


if __name__ == "__main__":
    test_freshness_moves_the_right_way()
    print("OK: watchdog sanity test passed.")