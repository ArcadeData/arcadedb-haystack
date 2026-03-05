# SPDX-FileCopyrightText: 2026-present ArcadeData Ltd <info@arcadedb.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for filter conversion (no ArcadeDB instance required)."""

import unittest

from haystack_integrations.document_stores.arcadedb.filters import _convert_filters


class TestFilterConversion(unittest.TestCase):

    def test_none_returns_empty(self):
        self.assertEqual(_convert_filters(None), "")

    def test_equality(self):
        result = _convert_filters({"field": "meta.name", "operator": "==", "value": "alice"})
        self.assertEqual(result, "meta.name = 'alice'")

    def test_equality_null(self):
        result = _convert_filters({"field": "meta.name", "operator": "==", "value": None})
        self.assertEqual(result, "meta.name IS NULL")

    def test_not_equal(self):
        result = _convert_filters({"field": "meta.name", "operator": "!=", "value": "bob"})
        self.assertEqual(result, "meta.name <> 'bob'")

    def test_not_equal_null(self):
        result = _convert_filters({"field": "meta.name", "operator": "!=", "value": None})
        self.assertEqual(result, "meta.name IS NOT NULL")

    def test_greater_than(self):
        result = _convert_filters({"field": "meta.score", "operator": ">", "value": 5})
        self.assertEqual(result, "meta.score > 5")

    def test_in_operator(self):
        result = _convert_filters({"field": "meta.tag", "operator": "in", "value": ["a", "b"]})
        self.assertEqual(result, "meta.tag IN ['a', 'b']")

    def test_not_in_operator(self):
        result = _convert_filters({"field": "meta.tag", "operator": "not in", "value": ["x"]})
        self.assertEqual(result, "meta.tag NOT IN ['x']")

    def test_and(self):
        result = _convert_filters({
            "operator": "AND",
            "conditions": [
                {"field": "meta.a", "operator": "==", "value": 1},
                {"field": "meta.b", "operator": ">", "value": 2},
            ],
        })
        self.assertEqual(result, "(meta.a = 1 AND meta.b > 2)")

    def test_or(self):
        result = _convert_filters({
            "operator": "OR",
            "conditions": [
                {"field": "meta.x", "operator": "==", "value": "yes"},
                {"field": "meta.y", "operator": "==", "value": "no"},
            ],
        })
        self.assertEqual(result, "(meta.x = 'yes' OR meta.y = 'no')")

    def test_not(self):
        result = _convert_filters({
            "operator": "NOT",
            "conditions": [
                {"field": "meta.deleted", "operator": "==", "value": True},
            ],
        })
        self.assertEqual(result, "NOT (meta.deleted = true)")

    def test_nested(self):
        result = _convert_filters({
            "operator": "AND",
            "conditions": [
                {"field": "meta.a", "operator": "==", "value": 1},
                {
                    "operator": "OR",
                    "conditions": [
                        {"field": "meta.b", "operator": "==", "value": 2},
                        {"field": "meta.c", "operator": "==", "value": 3},
                    ],
                },
            ],
        })
        self.assertEqual(result, "(meta.a = 1 AND (meta.b = 2 OR meta.c = 3))")

    def test_missing_operator_raises(self):
        with self.assertRaises(ValueError):
            _convert_filters({"field": "x", "value": 1})

    def test_missing_field_raises(self):
        with self.assertRaises(ValueError):
            _convert_filters({"operator": "==", "value": 1})


if __name__ == "__main__":
    unittest.main()
