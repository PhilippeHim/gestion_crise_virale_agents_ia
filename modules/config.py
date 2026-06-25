from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class InputConfig:
    path: str
    sheet_name: str | int | None = 0


@dataclass(frozen=True)
class FilterConfig:
    column: str
    op: str
    value: Any = None


@dataclass(frozen=True)
class AgentConfig:
    name: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineConfig:
    input: InputConfig
    filters: list[FilterConfig] = field(default_factory=list)
    agents: list[AgentConfig] = field(default_factory=list)


def load_config(path: str | Path) -> PipelineConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    input_raw = raw.get("input", {})
    return PipelineConfig(
        input=InputConfig(
            path=input_raw["path"],
            sheet_name=input_raw.get("sheet_name", 0),
        ),
        filters=[FilterConfig(**item) for item in raw.get("filters", [])],
        agents=[
            AgentConfig(name=item["name"], params=item.get("params", {}))
            for item in raw.get("agents", [])
        ],
    )
