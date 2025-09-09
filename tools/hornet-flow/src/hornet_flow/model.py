from typing import Any
import jsonschema


_metadata_model_schema = {
    "$defs": {
        "Release": {
            "properties": {
                "origin": {"title": "Origin", "type": "string"},
                "url": {
                    "format": "uri",
                    "maxLength": 2083,
                    "minLength": 1,
                    "title": "Url",
                    "type": "string",
                },
                "label": {"title": "Label", "type": "string"},
                "marker": {"title": "Marker", "type": "string"},
            },
            "required": ["origin", "url", "label", "marker"],
            "title": "Release",
            "type": "object",
        }
    },
    "additionalProperties": True,
    "properties": {"release": {"$ref": "#/$defs/Release"}},
    "required": ["release"],
    "title": "Metadata",
    "type": "object",
}


def validate_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    jsonschema.validate(instance=metadata, schema=_metadata_model_schema)
    return metadata
