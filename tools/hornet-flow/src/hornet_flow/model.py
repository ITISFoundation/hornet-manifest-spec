from dataclasses import dataclass, field
from typing import Any, List, Literal, TypeAlias

import jsonschema

IDStr: TypeAlias = str  # For clarity in type hints


@dataclass
class File:
    """Represents a file in a component."""

    path: str
    type: Literal["solidworks_part", "solidworks_assembly", "step_export"]


@dataclass
class Component:
    """Represents a component in the CAD manifest."""

    id: IDStr
    type: Literal["assembly", "part"]
    description: str
    files: List[File]
    components: List["Component"] = field(default_factory=list)  # Only for assemblies

    # Extras
    parent_path: List[IDStr] = field(
        default_factory=list
    )  # Path to parent component from root e.g. ["compA", "subCompB"]


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


@dataclass
class Release:
    origin: str
    url: str
    label: str
    marker: str


def validate_metadata_and_get_release(metadata: dict[str, Any]) -> Release:
    jsonschema.validate(instance=metadata, schema=_metadata_model_schema)
    return Release(**metadata["release"])
