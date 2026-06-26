from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components


_COMPONENT_DIR = Path(__file__).resolve().parent / "frontend" / "build"
_component = components.declare_component(
    "pipeline_timeline_selector",
    path=str(_COMPONENT_DIR),
)


def timeline_selector(
    *,
    steps: list[dict[str, Any]],
    pipeline_stages: list[dict[str, Any]] | None = None,
    tabs: list[dict[str, str]],
    active_tab: str,
    dataset_label: str,
    key: str = "pipeline_timeline",
) -> dict[str, Any] | None:
    default_value = {
        "selectedColumn": None,
        "activeTab": active_tab,
        "computeBackend": "cpu",
        "useWeights": False,
        "weightColumn": None,
        "targetColumn": None,
        "yearStart": None,
        "yearEnd": None,
    }
    return _component(
        steps=steps,
        pipelineStages=pipeline_stages or [],
        columns=[],
        selectedColumn=None,
        datasetLabel=dataset_label,
        tabs=tabs,
        activeTab=active_tab,
        computeBackend="cpu",
        weightColumns=[],
        useWeights=False,
        weightColumn=None,
        targetColumn=None,
        targetColumns=[],
        yearColumn=None,
        yearMin=None,
        yearMax=None,
        yearStart=None,
        yearEnd=None,
        default=default_value,
        key=key,
    )
