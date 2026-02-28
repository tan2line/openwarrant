"""Tests for action_matches — wildcard matching on dot-separated paths."""

from openwarrant.action_matcher import action_matches


def test_exact_match():
    assert action_matches("cds.alert.sepsis", "cds.alert.sepsis") is True


def test_exact_no_match():
    assert action_matches("cds.alert.sepsis", "cds.alert.other") is False


def test_wildcard_single_level():
    assert action_matches("cds.alert.*", "cds.alert.sepsis") is True
    assert action_matches("cds.alert.*", "cds.alert.deterioration") is True
    assert action_matches("cds.alert.*", "cds.recommend.medication") is False


def test_wildcard_multi_level():
    assert action_matches("cds.*", "cds.alert.sepsis") is True
    assert action_matches("cds.*", "cds.recommend.medication") is True
    assert action_matches("cds.*", "doc.generate") is False


def test_global_wildcard():
    assert action_matches("*", "cds.alert.sepsis") is True
    assert action_matches("*", "anything.at.all") is True


def test_pattern_longer_than_action():
    assert action_matches("cds.alert.sepsis.detail", "cds.alert.sepsis") is False


def test_action_longer_than_pattern_no_wildcard():
    assert action_matches("cds.alert", "cds.alert.sepsis") is False


def test_single_segment_exact():
    assert action_matches("read", "read") is True
    assert action_matches("read", "write") is False
