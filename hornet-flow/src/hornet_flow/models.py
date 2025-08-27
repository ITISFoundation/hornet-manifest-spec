# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring


from __future__ import annotations

from enum import Enum
from typing import Annotated, List, Literal, Union

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, HttpUrl

#
# CAD manifest
#


class Type(Enum):
    solidworks_part = "solidworks_part"
    solidworks_assembly = "solidworks_assembly"
    step_export = "step_export"


class File(BaseModel):
    path: str
    type: Type


class Part(BaseModel):
    id: str
    type: Literal["part"]
    description: str
    files: List[File]


class Component(BaseModel):
    __root__: Union[Assembly, Part] = Field(..., discriminator="type")


class HornetCadManifest(BaseModel):
    """HORNET CAD manifest"""

    repository: Annotated[
        AnyUrl, Field(description="The URL of the repository containing the CAD files.")
    ]
    components: Annotated[
        list[Component],
        Field(description="Top-level components in this CAD project.", min_items=1),
    ]


class Assembly(BaseModel):
    id: Annotated[
        str, Field(description="Unique identifier for the component", min_length=1)
    ]
    type: Literal["assembly"]
    description: str
    files: list[File]
    components: list[Component]


Component.update_forward_refs()


#
# Relevant parts of the portal metadata file
#
class Release(BaseModel):
    origin: str
    url: HttpUrl
    label: str
    marker: str


class Metadata(BaseModel):
    release: Release
    model_config = ConfigDict(extra="allow")  # accept extra keys
