from typing import Literal
from pydantic import BaseModel, ConfigDict, HttpUrl


class Release(BaseModel):
    origin: str
    url: HttpUrl
    label: str
    marker: str


class Metadata(BaseModel):
    release: Release
    model_config = ConfigDict(extra="allow")  # accept extra keys
