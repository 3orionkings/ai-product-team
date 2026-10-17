"""Unit tests for ai_product_team.validation.

Covers every supported keyword (positive and negative), schema defects (unsupported keyword, bad keyword
value, bad $ref), local $ref resolution including recursion and escaped tokens, the error pointer format,
load_schema caching and failure modes, and ensure_valid. Temporary schema directories use tempfile.
"""

from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from ai_product_team import validation as V
from ai_product_team.errors import NotFoundError, ValidationError

ERROR_RE = re.compile(r"^/.*?: .+$")


class Base(unittest.TestCase):
    def assertValid(self, instance, schema, root=None):
        errors = V.validate(instance, schema, root=root)
        self.assertEqual([], errors)

    def assertErrors(self, instance, schema, *fragments, root=None):
        errors = V.validate(instance, schema, root=root)
        self.assertTrue(errors, "expected validation errors")
        for err in errors:
            self.assertRegex(err, ERROR_RE)
        for fragment in fragments:
            self.assertTrue(any(fragment in e for e in errors), f"{fragment!r} not in {errors!r}")
        return errors

    def assertDefect(self, instance, schema, fragment=None):
        with self.assertRaises(ValidationError) as ctx:
            V.validate(instance, schema)
        if fragment:
            self.assertIn(fragment, str(ctx.exception))
        return ctx.exception


class TypeKeyword(Base):
    def test_each_type_name(self):
        cases = {
            "null": (None, 0),
            "boolean": (True, "true"),
            "integer": (3, 3.5),
            "number": (3.5, "3.5"),
            "string": ("x", 1),
            "array": ([], {}),
            "object": ({}, []),
        }
        for name, (good, bad) in cases.items():
            self.assertValid(good, {"type": name})
            self.assertErrors(bad, {"type": name}, f"is not of type '{name}'")

    def test_integer_is_distinct_from_number_and_bool(self):
        self.assertValid(1, {"type": "number"})
        self.assertValid(1.0, {"type": "integer"})
        self.assertErrors(1.5, {"type": "integer"}, "1.5 is not of type 'integer'")
        self.assertErrors(True, {"type": "integer"})
        self.assertErrors(False, {"type": "number"})
        self.assertErrors(1, {"type": "boolean"})

    def test_type_list(self):
        schema = {"type": ["string", "null"]}
        self.assertValid("x", schema)
        self.assertValid(None, schema)
        self.assertErrors(1, schema, "1 is not of type 'string', 'null'")

    def test_unknown_type_name_is_a_schema_defect(self):
        self.assertDefect("x", {"type": "text"}, "unknown type name")
        self.assertDefect("x", {"type": []})


class ObjectKeywords(Base):
    SCHEMA = {
        "type": "object",
        "properties": {"a": {"type": "integer"}, "b": {"type": "string"}},
        "required": ["a", "b"],
        "additionalProperties": False,
    }

    def test_properties_and_required_positive(self):
        self.assertValid({"a": 1, "b": "x"}, self.SCHEMA)

    def test_required_reported_at_property_pointer(self):
        errors = self.assertErrors({"a": 1}, self.SCHEMA, "/b: 'b' is a required property")
        self.assertEqual(1, len(errors))

    def test_nested_required_pointer(self):
        schema = {"properties": {"budget": {"required": ["max_steps"]}}}
        self.assertErrors({"budget": {}}, schema, "/budget/max_steps: 'max_steps' is a required property")

    def test_properties_only_checked_when_present(self):
        self.assertValid({}, {"properties": {"a": {"type": "integer"}}})
        self.assertErrors({"a": "no"}, {"properties": {"a": {"type": "integer"}}}, "/a: 'no' is not of type 'integer'")

    def test_additional_properties_false(self):
        self.assertErrors({"a": 1, "b": "x", "c": 3}, self.SCHEMA, "/c: additional property 'c' is not allowed")

    def test_additional_properties_true_and_absent(self):
        self.assertValid({"a": 1, "c": 3}, {"properties": {"a": {}}, "additionalProperties": True})
        self.assertValid({"a": 1, "c": 3}, {"properties": {"a": {}}})

    def test_additional_properties_schema(self):
        schema = {"properties": {"a": {}}, "additionalProperties": {"type": "boolean"}}
        self.assertValid({"a": 1, "flag": True}, schema)
        self.assertErrors({"a": 1, "flag": "yes"}, schema, "/flag: 'yes' is not of type 'boolean'")

    def test_object_keywords_ignored_for_non_objects(self):
        self.assertValid("text", {"required": ["a"], "additionalProperties": False})

    def test_malformed_required_is_a_defect(self):
        self.assertDefect({}, {"required": "a"}, "required")
        self.assertDefect({}, {"properties": []}, "properties")


class EnumAndConst(Base):
    def test_enum_positive_and_negative_with_contract_message(self):
        schema = {"properties": {"status": {"enum": ["complete", "needs_input"]}}}
        self.assertValid({"status": "complete"}, schema)
        errors = self.assertErrors({"status": "done"}, schema)
        self.assertEqual(["/status: 'done' is not one of ['complete', 'needs_input']"], errors)

    def test_enum_distinguishes_bool_from_int(self):
        self.assertErrors(True, {"enum": [1]})
        self.assertErrors(1, {"enum": [True]})
        self.assertValid(1.0, {"enum": [1]})
        self.assertValid(None, {"enum": [None]})
        self.assertValid({"a": [1, "b"]}, {"enum": [{"a": [1, "b"]}]})

    def test_enum_must_be_array(self):
        self.assertDefect("x", {"enum": "x"}, "enum")

    def test_const(self):
        self.assertValid("command_exit_status_only", {"const": "command_exit_status_only"})
        self.assertErrors("other", {"const": "command_exit_status_only"}, "is not the constant 'command_exit_status_only'")
        self.assertValid({"k": [1, 2]}, {"const": {"k": [1, 2]}})
        self.assertErrors(1, {"const": True})


class ArrayKeywords(Base):
    def test_items_with_index_pointer(self):
        schema = {"items": {"type": "string"}}
        self.assertValid(["a", "b"], schema)
        self.assertValid([], schema)
        errors = self.assertErrors(["a", 2, "c", 4.5], schema, "/1: 2 is not of type 'string'", "/3: 4.5 is not of type 'string'")
        self.assertEqual(2, len(errors))

    def test_min_and_max_items(self):
        self.assertValid([1, 2], {"minItems": 2, "maxItems": 2})
        self.assertErrors([1], {"minItems": 2}, "array has 1 item(s) but minItems is 2")
        self.assertErrors([1, 2, 3], {"maxItems": 2}, "array has 3 item(s) but maxItems is 2")
        self.assertDefect([], {"minItems": -1}, "minItems")
        self.assertDefect([], {"maxItems": True}, "maxItems")

    def test_unique_items(self):
        self.assertValid([1, 2, 3], {"uniqueItems": True})
        self.assertValid([1, True], {"uniqueItems": True})
        self.assertValid([1, 1], {"uniqueItems": False})
        self.assertErrors([1, 2, 1], {"uniqueItems": True}, "array items are not unique")
        self.assertErrors([{"a": 1}, {"a": 1}], {"uniqueItems": True}, "not unique")
        self.assertErrors([1, 1.0], {"uniqueItems": True})
        self.assertDefect([], {"uniqueItems": "yes"}, "uniqueItems")

    def test_array_keywords_ignored_for_non_arrays(self):
        self.assertValid("abc", {"minItems": 10, "items": {"type": "integer"}})

    def test_items_must_be_single_schema(self):
        self.assertDefect([1], {"items": [{"type": "integer"}]}, "items")


class StringKeywords(Base):
    def test_pattern_uses_search_semantics(self):
        self.assertValid("abc", {"pattern": "^a"})
        self.assertValid("xabc", {"pattern": "b"})
        self.assertErrors("bac", {"pattern": "^a"}, "'bac' does not match pattern '^a'")
        self.assertValid("human-owner", {"pattern": "^[a-z][a-z0-9-]*$"})
        self.assertErrors("Human Owner", {"pattern": "^[a-z][a-z0-9-]*$"})

    def test_invalid_pattern_is_a_defect(self):
        self.assertDefect("x", {"pattern": "("}, "regular expression")
        self.assertDefect("x", {"pattern": 3}, "pattern")

    def test_min_and_max_length_count_code_points(self):
        self.assertValid("héllo", {"minLength": 5, "maxLength": 5})
        self.assertErrors("", {"minLength": 1}, "'' is shorter than minLength 1")
        self.assertErrors("a" * 53, {"maxLength": 52}, "is longer than maxLength 52")
        self.assertDefect("x", {"minLength": -2}, "minLength")

    def test_string_keywords_ignored_for_non_strings(self):
        self.assertValid(5, {"minLength": 10, "pattern": "^z"})


class NumberKeywords(Base):
    def test_minimum_and_maximum(self):
        self.assertValid(5, {"minimum": 5, "maximum": 5})
        self.assertValid(2.5, {"minimum": 2, "maximum": 3})
        self.assertErrors(4, {"minimum": 5}, "4 is less than minimum 5")
        self.assertErrors(6.5, {"maximum": 6}, "6.5 is greater than maximum 6")

    def test_bounds_ignore_booleans_and_strings(self):
        self.assertValid(True, {"minimum": 5})
        self.assertValid("9", {"maximum": 1})

    def test_non_numeric_bound_is_a_defect(self):
        self.assertDefect(1, {"minimum": "0"}, "minimum")


class FormatKeyword(Base):
    def test_date_time_positive(self):
        for value in ("2026-10-16T20:54:00Z", "2026-10-16T20:54:00.123Z", "2026-10-16T20:54:00+02:00", "2026-10-16t20:54:00-05:30"):
            self.assertValid(value, {"format": "date-time"})

    def test_date_time_negative(self):
        for value in ("2026-10-16T20:54:00", "2026-10-16", "2026-10-16 20:54:00Z", "yesterday", "2026-13-01T00:00:00Z", ""):
            self.assertErrors(value, {"format": "date-time"}, "is not a valid date-time")

    def test_other_formats_are_recorded_not_enforced(self):
        for fmt in ("email", "uri", "uuid", "ipv4", "made-up"):
            self.assertValid("definitely not valid for any format", {"format": fmt})

    def test_format_ignored_for_non_strings(self):
        self.assertValid(None, {"format": "date-time"})
        self.assertValid(None, {"type": ["string", "null"], "format": "date-time"})

    def test_format_must_be_string(self):
        self.assertDefect("x", {"format": 1}, "format")


class Combinators(Base):
    def test_one_of(self):
        schema = {"oneOf": [{"type": "integer"}, {"type": "string"}]}
        self.assertValid(1, schema)
        self.assertValid("x", schema)
        self.assertErrors(None, schema, "is not valid under any oneOf schema")
        both = {"oneOf": [{"type": "number"}, {"type": "integer"}]}
        self.assertErrors(1, both, "is valid under 2 oneOf schemas; exactly one is required")
        self.assertValid(1.5, both)

    def test_any_of(self):
        schema = {"anyOf": [{"type": "number"}, {"type": "integer"}, {"type": "string"}]}
        self.assertValid(1, schema)
        self.assertValid("x", schema)
        self.assertErrors([], schema, "is not valid under any anyOf schema")

    def test_all_of_reports_each_branch_error_at_instance_pointer(self):
        schema = {"properties": {"n": {"allOf": [{"type": "integer"}, {"minimum": 10}]}}}
        self.assertValid({"n": 10}, schema)
        errors = self.assertErrors({"n": 3}, schema, "/n: 3 is less than minimum 10")
        self.assertEqual(1, len(errors))
        errors = self.assertErrors({"n": 3.5}, schema, "/n: 3.5 is not of type 'integer'", "/n: 3.5 is less than minimum 10")
        self.assertEqual(2, len(errors))

    def test_not(self):
        self.assertValid("x", {"not": {"type": "integer"}})
        self.assertErrors(1, {"not": {"type": "integer"}}, "must not be valid under the 'not' schema")

    def test_combinators_require_non_empty_arrays(self):
        self.assertDefect(1, {"oneOf": []}, "oneOf")
        self.assertDefect(1, {"anyOf": {}}, "anyOf")
        self.assertDefect(1, {"allOf": []}, "allOf")


class RefResolution(Base):
    def test_defs_ref_positive_and_negative(self):
        schema = {
            "properties": {"status": {"$ref": "#/$defs/status"}},
            "$defs": {"status": {"type": "string", "enum": ["complete", "blocked"]}},
        }
        self.assertValid({"status": "complete"}, schema)
        self.assertErrors({"status": "done"}, schema, "/status: 'done' is not one of ['complete', 'blocked']")

    def test_ref_chain_and_sibling_keywords(self):
        schema = {
            "properties": {"n": {"$ref": "#/$defs/a", "maximum": 5}},
            "$defs": {"a": {"$ref": "#/$defs/b"}, "b": {"type": "integer", "minimum": 1}},
        }
        self.assertValid({"n": 3}, schema)
        self.assertErrors({"n": 0}, schema, "/n: 0 is less than minimum 1")
        self.assertErrors({"n": 9}, schema, "/n: 9 is greater than maximum 5")
        self.assertErrors({"n": "x"}, schema, "is not of type 'integer'")

    def test_recursive_root_ref(self):
        tree = {
            "type": "object",
            "required": ["label"],
            "properties": {"label": {"type": "string"}, "children": {"type": "array", "items": {"$ref": "#"}}},
            "additionalProperties": False,
        }
        self.assertValid({"label": "root", "children": [{"label": "leaf"}, {"label": "mid", "children": []}]}, tree)
        self.assertErrors(
            {"label": "root", "children": [{"label": "ok"}, {"children": [{"label": 3}]}]},
            tree,
            "/children/1/label: 'label' is a required property",
            "/children/1/children/0/label: 3 is not of type 'string'",
        )

    def test_ref_into_properties_and_escaped_tokens(self):
        schema = {
            "properties": {"x": {"type": "integer"}, "y": {"$ref": "#/properties/x"}, "z": {"$ref": "#/$defs/a~1b"}, "w": {"$ref": "#/$defs/t~0k"}, "v": {"$ref": "#/$defs/a%20b"}},
            "$defs": {"a/b": {"const": "slash"}, "t~k": {"const": "tilde"}, "a b": {"const": "space"}},
        }
        self.assertValid({"x": 1, "y": 2, "z": "slash", "w": "tilde", "v": "space"}, schema)
        self.assertErrors({"y": "no"}, schema, "/y: 'no' is not of type 'integer'")
        self.assertErrors({"z": "x"}, schema, "/z: 'x' is not the constant 'slash'")

    def test_explicit_root_argument(self):
        root = {"$defs": {"id": {"type": "string", "minLength": 1}}}
        self.assertValid("abc", {"$ref": "#/$defs/id"}, root=root)
        self.assertErrors("", {"$ref": "#/$defs/id"}, "shorter than minLength 1", root=root)

    def test_unresolvable_ref_is_a_defect(self):
        self.assertDefect({}, {"$ref": "#/$defs/missing"}, "unresolvable $ref")
        self.assertDefect({}, {"$ref": "#/$defs/a/9", "$defs": {"a": [1]}}, "unresolvable")

    def test_non_local_ref_is_a_defect(self):
        for ref in ("common.schema.json#/$defs/x", "https://aipt.local/schemas/claim", "#defs/x", "", 7):
            with self.subTest(ref=ref):
                self.assertDefect({}, {"$ref": ref}, "only local $ref")

    def test_circular_ref_without_progress_is_a_defect(self):
        self.assertDefect({}, {"$ref": "#"}, "circular $ref")
        self.assertDefect(1, {"$defs": {"a": {"$ref": "#/$defs/b"}, "b": {"$ref": "#/$defs/a"}}, "$ref": "#/$defs/a"}, "circular")


class UnsupportedKeywords(Base):
    def test_validate_raises_on_unsupported_keyword(self):
        exc = self.assertDefect({}, {"patternProperties": {"^x": {}}}, "unsupported schema keyword")
        self.assertEqual(["patternProperties"], exc.details["keywords"])
        self.assertEqual(["/: unsupported schema keyword 'patternProperties'"], exc.errors)

    def test_nested_unsupported_keyword_detected_when_reached(self):
        schema = {"properties": {"a": {"if": {"type": "string"}}}}
        self.assertValid({}, schema)
        self.assertDefect({"a": 1}, schema, "'if'")

    def test_every_draft_keyword_outside_subset_is_rejected(self):
        for kw in ("if", "then", "else", "dependentRequired", "dependentSchemas", "prefixItems", "contains", "minContains", "maxContains", "patternProperties", "propertyNames", "minProperties", "maxProperties", "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "unevaluatedProperties", "unevaluatedItems", "$anchor", "$dynamicRef", "$comment", "contentMediaType", "readOnly", "deprecated"):
            with self.subTest(keyword=kw):
                self.assertDefect({}, {kw: True})

    def test_schema_keyword_errors_walks_structure(self):
        schema = {
            "type": "object",
            "properties": {"patternProperties": {"type": "string"}, "b": {"items": {"minContains": 1}}},
            "$defs": {"if": {"type": "string"}, "d": {"oneOf": [{"type": "string"}, {"contains": {}}]}},
            "additionalProperties": {"propertyNames": {}},
            "not": {"then": {}},
        }
        found = V.schema_keyword_errors(schema)
        self.assertEqual(
            [
                "/properties/b/items/minContains: unsupported keyword 'minContains'",
                "/$defs/d/oneOf/1/contains: unsupported keyword 'contains'",
                "/additionalProperties/propertyNames: unsupported keyword 'propertyNames'",
                "/not/then: unsupported keyword 'then'",
            ],
            found,
        )
        self.assertEqual([], V.schema_keyword_errors({"properties": {"if": {"enum": [{"then": 1}]}}, "default": {"x": 1}, "examples": [{"if": 1}]}))

    def test_supported_keyword_set_is_the_contract_list(self):
        contract = {
            "$schema", "$id", "title", "description", "$defs", "$ref", "type", "properties", "required", "additionalProperties",
            "enum", "const", "items", "minItems", "maxItems", "uniqueItems", "pattern", "minLength", "maxLength", "minimum",
            "maximum", "format", "oneOf", "anyOf", "allOf", "not", "default", "examples",
        }
        self.assertEqual(contract, set(V.SUPPORTED_KEYWORDS))


class IgnoredKeywordsAndBooleanSchemas(Base):
    def test_annotations_have_no_effect(self):
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://aipt.local/schemas/x", "title": "T", "description": "D", "default": 5, "examples": [1, "two"], "type": "string"}
        self.assertValid("ok", schema)
        self.assertErrors(5, schema, "is not of type 'string'")

    def test_boolean_schemas(self):
        self.assertValid({"anything": 1}, True)
        self.assertErrors(1, False, "false schema does not allow any value")
        self.assertValid([], {"items": False})
        self.assertErrors([1], {"items": False}, "/0: false schema does not allow any value")
        self.assertValid({"a": 1}, {"properties": {"a": True}})

    def test_non_schema_value_is_a_defect(self):
        self.assertDefect({"a": 1}, {"properties": {"a": "string"}}, "schema must be an object or boolean")


class PointerFormat(Base):
    def test_root_pointer_renders_as_slash(self):
        self.assertEqual(["/: 'x' is not of type 'integer'"], V.validate("x", {"type": "integer"}))

    def test_nested_and_indexed_pointers(self):
        schema = {"properties": {"items": {"items": {"properties": {"n": {"type": "integer"}}}}}}
        self.assertEqual(["/items/1/n: 'x' is not of type 'integer'"], V.validate({"items": [{"n": 1}, {"n": "x"}]}, schema))

    def test_pointer_escapes_slash_and_tilde(self):
        schema = {"properties": {"a/b": {"type": "integer"}, "t~k": {"type": "integer"}}}
        errors = V.validate({"a/b": "x", "t~k": "y"}, schema)
        self.assertEqual(["/a~1b: 'x' is not of type 'integer'", "/t~0k: 'y' is not of type 'integer'"], errors)

    def test_all_errors_have_pointer_colon_space_message(self):
        schema = {"type": "object", "required": ["a"], "properties": {"b": {"enum": [1]}, "c": {"items": {"minimum": 2}}}, "additionalProperties": False}
        errors = V.validate({"b": 2, "c": [1, 5, 0], "d": None}, schema)
        self.assertEqual(5, len(errors))
        for err in errors:
            self.assertRegex(err, ERROR_RE)
            pointer, _, message = err.partition(": ")
            self.assertTrue(pointer.startswith("/"))
            self.assertTrue(message)

    def test_errors_are_deterministic_and_schema_is_not_mutated(self):
        schema = {"type": "object", "required": ["a", "b"], "properties": {"a": {"type": "integer"}}, "additionalProperties": False}
        before = copy.deepcopy(schema)
        first = V.validate({"a": "x", "z": 1}, schema)
        second = V.validate({"a": "x", "z": 1}, schema)
        self.assertEqual(first, second)
        self.assertEqual(before, schema)
        self.assertEqual(["/b: 'b' is a required property", "/a: 'x' is not of type 'integer'", "/z: additional property 'z' is not allowed"], first)

    def test_long_values_are_truncated_in_messages(self):
        errors = V.validate("x" * 500, {"type": "integer"})
        self.assertEqual(1, len(errors))
        self.assertLess(len(errors[0]), 200)
        self.assertIn("...", errors[0])


class LoadSchema(unittest.TestCase):
    def test_loads_and_caches_real_schema(self):
        first = V.load_schema("claim")
        second = V.load_schema("claim")
        self.assertIs(first, second)
        self.assertEqual("https://aipt.local/schemas/claim", first["$id"])

    def test_missing_schema_is_not_found(self):
        with self.assertRaises(NotFoundError) as ctx:
            V.load_schema("no-such-schema")
        self.assertEqual("not_found", ctx.exception.code)
        self.assertEqual("no-such-schema", ctx.exception.details["name"])

    def test_unsafe_or_malformed_names_are_not_found(self):
        for name in ("", "../claim", "claim.schema", "Claim", "claim/x", "schemas/claim", 5, None):
            with self.subTest(name=name):
                with self.assertRaises(NotFoundError):
                    V.load_schema(name)  # type: ignore[arg-type]

    def test_temporary_schema_dir_failure_modes(self):
        original = V.SCHEMAS_DIR
        names = ("zz-tmp-ok", "zz-tmp-badkw", "zz-tmp-badjson", "zz-tmp-list")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "zz-tmp-ok.schema.json").write_text(json.dumps({"$id": "x", "type": "integer"}), encoding="utf-8")
            (root / "zz-tmp-badkw.schema.json").write_text(json.dumps({"properties": {"a": {"if": {}}}}), encoding="utf-8")
            (root / "zz-tmp-badjson.schema.json").write_text("{not json", encoding="utf-8")
            (root / "zz-tmp-list.schema.json").write_text("[]", encoding="utf-8")
            V.SCHEMAS_DIR = root
            try:
                self.assertEqual({"$id": "x", "type": "integer"}, V.load_schema("zz-tmp-ok"))
                with self.assertRaises(ValidationError) as ctx:
                    V.load_schema("zz-tmp-badkw")
                self.assertEqual(["/properties/a/if: unsupported keyword 'if'"], ctx.exception.errors)
                with self.assertRaises(ValidationError):
                    V.load_schema("zz-tmp-badjson")
                with self.assertRaises(ValidationError):
                    V.load_schema("zz-tmp-list")
                with self.assertRaises(NotFoundError):
                    V.load_schema("zz-tmp-absent")
            finally:
                V.SCHEMAS_DIR = original
                for name in names:
                    V._SCHEMA_CACHE.pop(name, None)


class EnsureValid(unittest.TestCase):
    CLAIM = {
        "statement": "Drafts only.",
        "claim_type": "fact",
        "status": "supported",
        "supporting_refs": ["ver_1"],
        "contrary_refs": [],
        "confidence_label": "high",
        "assessed_by": "claim-checker",
    }

    def test_valid_instance_returns_none(self):
        self.assertIsNone(V.ensure_valid(self.CLAIM, "claim"))

    def test_invalid_instance_raises_with_all_errors(self):
        bad = dict(self.CLAIM, status="done", confidence_label="certain", extra=1)
        with self.assertRaises(ValidationError) as ctx:
            V.ensure_valid(bad, "claim")
        exc = ctx.exception
        self.assertEqual("validation", exc.code)
        self.assertEqual("claim", exc.details["schema"])
        self.assertEqual(exc.errors, exc.details["errors"])
        self.assertEqual(3, len(exc.errors))
        self.assertIn("/status: 'done' is not one of ['proposed', 'supported', 'contested', 'unsupported', 'superseded']", exc.errors)
        self.assertIn("/confidence_label: 'certain' is not one of ['low', 'medium', 'high', 'unknown']", exc.errors)
        self.assertIn("/extra: additional property 'extra' is not allowed", exc.errors)
        self.assertIn("3 validation error(s)", str(exc))

    def test_unknown_schema_name_is_not_found(self):
        with self.assertRaises(NotFoundError):
            V.ensure_valid({}, "nope")


if __name__ == "__main__":
    unittest.main()
