from dataclasses import dataclass, field
from typing import Any, List, Literal

import jsonschema


@dataclass
class File:
    """Represents a file in a component."""

    path: str
    type: Literal["solidworks_part", "solidworks_assembly", "step_export"]


@dataclass
class Component:
    """Represents a component in the CAD manifest."""

    id: str
    type: Literal["assembly", "part"]
    description: str
    files: List[File]
    components: List["Component"] = field(default_factory=list)  # Only for assemblies
    parent_id: List[str] = field(default_factory=list)  # Path to parent components


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
