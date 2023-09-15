from aenum import Enum, NoAlias
from typing import Any, Optional, TypedDict


class Units(Enum, settings=NoAlias):
    mm = 1e-3
    mrad = 1e-3
    um = 1e-6
    nm = 1e-9

    def __str__(self) -> str:
        return self.name


class Result(TypedDict):
    value: float
    units: Optional[Units]
    name: str
    equation: str


def parse_inputs(data: dict[str, Any]) -> dict[str, Any]:
    """Converts the units of the input data from strings to Units instances."""
    data = data.copy()
    for key, value in data.items():
        if key.endswith(".units"):
            data[key] = Units[value]
    return data
