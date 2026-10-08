from typing import Annotated

from pydantic import BaseModel, StringConstraints


SpeakerName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=50,
    ),
]


class SpeakerRename(BaseModel):
    current_name: SpeakerName
    new_name: SpeakerName
