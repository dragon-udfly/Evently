import uuid
from typing import Literal

Performative = Literal["REQUEST", "AGREE", "REFUSE", "PROPOSE", "INFORM", "FAILURE"]


def new_id() -> str:
    return uuid.uuid4().hex[:16]


