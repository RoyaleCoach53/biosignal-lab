"""Strict JSON objects for recording metadata and custom acquisition frames."""
import json


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Nonfinite JSON constants are not accepted")


def decode_json(payload):
    return json.loads(payload, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
