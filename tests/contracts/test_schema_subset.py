"""Contract test: every file under schemas/ uses only the keyword subset the validator implements.

The keyword list is copied here from docs/architecture/controller-contracts.md section 2 and the walk is
implemented independently of ai_product_team.validation, so drift in either direction fails. Also asserts
that every $ref is local and resolves within its own file.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from urllib.parse import unquote

from ai_product_team import validation as V

REPO = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO / "schemas"

SUPPORTED = frozenset(
    {
        "$schema", "$id", "title", "description", "$defs", "$ref",
        "type", "properties", "required", "additionalProperties",
        "enum", "const", "items", "minItems", "maxItems", "uniqueItems",
        "pattern", "minLength", "maxLength", "minimum", "maximum", "format",
        "oneOf", "anyOf", "allOf", "not", "default", "examples",
    }
)


def foreign_keywords(node, pointer: str = "") -> list[str]:
    """Independent structure-aware scan: names under properties/$defs are not keywords; data under enum/const/default/examples is not schema."""
    found: list[str] = []
    if isinstance(node, bool) or not isinstance(node, dict):
        return found
    for key, value in node.items():
        child = f"{pointer}/{key}"
        if key not in SUPPORTED:
            found.append(child)
            continue
        if key in ("properties", "$defs") and isinstance(value, dict):
            for name, sub in value.items():
                found.extend(foreign_keywords(sub, f"{child}/{name}"))
        elif key in ("items", "not"):
            found.extend(foreign_keywords(value, child))
        elif key == "additionalProperties" and not isinstance(value, bool):
            found.extend(foreign_keywords(value, child))
        elif key in ("oneOf", "anyOf", "allOf") and isinstance(value, list):
            for index, sub in enumerate(value):
                found.extend(foreign_keywords(sub, f"{child}/{index}"))
    return found


def refs(node, pointer: str = ""):
    """Yield (pointer, $ref) for every $ref in schema positions."""
    if isinstance(node, bool) or not isinstance(node, dict):
        return
    for key, value in node.items():
        child = f"{pointer}/{key}"
        if key == "$ref":
            yield child, value
        elif key in ("properties", "$defs") and isinstance(value, dict):
            for name, sub in value.items():
                yield from refs(sub, f"{child}/{name}")
        elif key in ("items", "not", "additionalProperties"):
            yield from refs(value, child)
        elif key in ("oneOf", "anyOf", "allOf") and isinstance(value, list):
            for index, sub in enumerate(value):
                yield from refs(sub, f"{child}/{index}")


def resolve_local(ref: str, root: dict):
    if ref == "#":
        return root
    node = root
    for raw in ref[2:].split("/"):
        token = unquote(raw).replace("~1", "/").replace("~0", "~")
        node = node[int(token)] if isinstance(node, list) else node[token]
    return node


def schema_files() -> list[Path]:
    return sorted(SCHEMAS_DIR.glob("*.schema.json"))


class SchemaSubset(unittest.TestCase):
    def test_there_are_schema_files(self):
        self.assertTrue(schema_files())

    def test_validator_keyword_set_matches_contract(self):
        self.assertEqual(SUPPORTED, V.SUPPORTED_KEYWORDS)

    def test_every_schema_file_uses_only_supported_keywords(self):
        for path in schema_files():
            with self.subTest(file=path.name):
                schema = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(schema, dict)
                self.assertEqual([], foreign_keywords(schema), f"{path.name} uses unsupported keywords")
                self.assertEqual([], V.schema_keyword_errors(schema))

    def test_every_schema_file_loads_through_the_validator(self):
        for path in schema_files():
            name = path.name[: -len(".schema.json")]
            with self.subTest(file=path.name):
                schema = V.load_schema(name)
                self.assertEqual(f"https://aipt.local/schemas/{name}", schema["$id"])

    def test_every_ref_is_local_and_resolves(self):
        for path in schema_files():
            schema = json.loads(path.read_text(encoding="utf-8"))
            for pointer, ref in refs(schema):
                with self.subTest(file=path.name, pointer=pointer):
                    self.assertIsInstance(ref, str)
                    self.assertTrue(ref == "#" or ref.startswith("#/"), f"non-local $ref {ref!r}")
                    target = resolve_local(ref, schema)
                    self.assertIsInstance(target, (dict, bool))

    def test_keyword_values_have_the_expected_shape(self):
        for path in schema_files():
            schema = json.loads(path.read_text(encoding="utf-8"))
            stack = [schema]
            while stack:
                node = stack.pop()
                if not isinstance(node, dict):
                    continue
                for key, value in node.items():
                    if key in ("properties", "$defs"):
                        self.assertIsInstance(value, dict, f"{path.name}: {key}")
                        stack.extend(value.values())
                    elif key in ("items", "not"):
                        stack.append(value)
                    elif key == "additionalProperties":
                        self.assertIsInstance(value, (bool, dict), f"{path.name}: additionalProperties")
                        stack.append(value)
                    elif key in ("oneOf", "anyOf", "allOf"):
                        self.assertIsInstance(value, list, f"{path.name}: {key}")
                        self.assertTrue(value, f"{path.name}: empty {key}")
                        stack.extend(value)
                    elif key in ("required", "enum"):
                        self.assertIsInstance(value, list, f"{path.name}: {key}")
                        self.assertTrue(value, f"{path.name}: empty {key}")
                    elif key in ("minItems", "maxItems", "minLength", "maxLength"):
                        self.assertIsInstance(value, int, f"{path.name}: {key}")
                        self.assertNotIsInstance(value, bool)
                        self.assertGreaterEqual(value, 0)
                    elif key in ("minimum", "maximum"):
                        self.assertIsInstance(value, (int, float), f"{path.name}: {key}")
                    elif key in ("pattern", "format", "title", "description", "$schema", "$id"):
                        self.assertIsInstance(value, str, f"{path.name}: {key}")
                    elif key == "uniqueItems":
                        self.assertIsInstance(value, bool, f"{path.name}: uniqueItems")
                    elif key == "type":
                        names = [value] if isinstance(value, str) else value
                        self.assertTrue(set(names) <= {"null", "boolean", "integer", "number", "string", "array", "object"}, f"{path.name}: type {value!r}")

    def test_scanner_detects_foreign_keywords(self):
        self.assertEqual(["/patternProperties"], foreign_keywords({"patternProperties": {}}))
        self.assertEqual(["/properties/a/if"], foreign_keywords({"properties": {"a": {"if": {}}}}))
        self.assertEqual(["/items/minContains"], foreign_keywords({"items": {"minContains": 1}}))
        self.assertEqual(["/oneOf/1/contains"], foreign_keywords({"oneOf": [{}, {"contains": {}}]}))
        self.assertEqual([], foreign_keywords({"properties": {"patternProperties": {"type": "string"}}, "$defs": {"if": {}}, "enum": [{"then": 1}]}))


if __name__ == "__main__":
    unittest.main()
