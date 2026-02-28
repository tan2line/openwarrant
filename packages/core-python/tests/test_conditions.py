"""Tests for evaluate_constraint — all 9 operators plus required."""

import pytest
from openwarrant.conditions import evaluate_constraint
from openwarrant.models import Constraint


def test_eq_string():
    c = Constraint(field="setting", operator="eq", value="icu")
    assert evaluate_constraint(c, {"setting": "icu"}) is True
    assert evaluate_constraint(c, {"setting": "ed"}) is False


def test_eq_number():
    c = Constraint(field="age", operator="eq", value=18)
    assert evaluate_constraint(c, {"age": 18}) is True
    assert evaluate_constraint(c, {"age": 19}) is False


def test_ne():
    c = Constraint(field="pregnant", operator="ne", value=True)
    assert evaluate_constraint(c, {"pregnant": False}) is True
    assert evaluate_constraint(c, {"pregnant": True}) is False


def test_in():
    c = Constraint(field="setting", operator="in", value=["icu", "ed"])
    assert evaluate_constraint(c, {"setting": "icu"}) is True
    assert evaluate_constraint(c, {"setting": "outpatient"}) is False


def test_not_in():
    c = Constraint(field="status", operator="not_in", value=["dnr"])
    assert evaluate_constraint(c, {"status": "active"}) is True
    assert evaluate_constraint(c, {"status": "dnr"}) is False


def test_gt():
    c = Constraint(field="confidence", operator="gt", value=0.8)
    assert evaluate_constraint(c, {"confidence": 0.9}) is True
    assert evaluate_constraint(c, {"confidence": 0.8}) is False


def test_gte():
    c = Constraint(field="age", operator="gte", value=18)
    assert evaluate_constraint(c, {"age": 18}) is True
    assert evaluate_constraint(c, {"age": 17}) is False


def test_lt():
    c = Constraint(field="egfr", operator="lt", value=30)
    assert evaluate_constraint(c, {"egfr": 29}) is True
    assert evaluate_constraint(c, {"egfr": 30}) is False


def test_lte():
    c = Constraint(field="score", operator="lte", value=0.5)
    assert evaluate_constraint(c, {"score": 0.5}) is True
    assert evaluate_constraint(c, {"score": 0.6}) is False


def test_contains():
    c = Constraint(field="diagnosis", operator="contains", value="sepsis")
    assert evaluate_constraint(c, {"diagnosis": "severe sepsis"}) is True
    assert evaluate_constraint(c, {"diagnosis": "pneumonia"}) is False


def test_required_present():
    c = Constraint(field="consent", operator="required", value=True)
    assert evaluate_constraint(c, {"consent": True}) is True
    assert evaluate_constraint(c, {"consent": "yes"}) is True


def test_required_missing():
    c = Constraint(field="consent", operator="required", value=True)
    assert evaluate_constraint(c, {}) is False
    assert evaluate_constraint(c, {"consent": False}) is False
    assert evaluate_constraint(c, {"consent": ""}) is False


def test_invalid_operator_raises():
    c = Constraint(field="x", operator="invalid", value=1)
    with pytest.raises(ValueError, match="Unknown operator"):
        evaluate_constraint(c, {"x": 1})


def test_missing_field_returns_false():
    c = Constraint(field="missing", operator="eq", value="x")
    assert evaluate_constraint(c, {"other": "y"}) is False
