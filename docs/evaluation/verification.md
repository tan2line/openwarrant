# Starter verification record

Verified September 5, 2026.

- New evaluation behavioral suite: **16 tests passed** on Python 3.12.
- Existing Python core: **55 tests passed**. Existing `datetime.utcnow()` deprecation warnings remain in the core audit module; that module was not changed.
- Existing TypeScript core: **8 tests passed**.
- Browser verification with headless Chromium: all 25 scenarios navigable; findings hidden initially; incomplete-export guard; 25 verdicts/rationales recorded; completed JSON review download; reviewer-specific draft restoration; category filtering; mobile width without horizontal overflow; no JavaScript page errors.
- Desktop and mobile screenshots inspected for legibility and layout.
- Known fixture comparison: baseline 20/25, candidate 21/25, three improved cases, two regressed cases, both automatic gates blocked.
- The test suite explicitly verifies that two agreeing uncertain reviewers cannot clear a run, that human passes cannot erase automated failures, and that even complete passing reviews cannot issue authorization.

The checks verify engineering behavior. The fixtures are hand-authored; no model API was called, no clinicians participated in validation, and no clinical performance claim follows from these tests. Browser verification used temporary tooling outside the package; the delivered reviewer desk has no runtime dependencies.
