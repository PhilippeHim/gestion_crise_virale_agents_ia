from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from datathon_pipeline.config import AgentConfig


@dataclass(frozen=True)
class AgentResult:
    name: str
    payload: dict[str, Any]


AgentHandler = Callable[[Any, dict[str, Any]], AgentResult]
_REGISTRY: dict[str, AgentHandler] = {}


def register_agent(name: str):
    def decorator(handler: AgentHandler) -> AgentHandler:
        _REGISTRY[name] = handler
        return handler

    return decorator


def run_agents(dataset, agents: list[AgentConfig]) -> list[AgentResult]:
    results: list[AgentResult] = []
    for agent_config in agents:
        handler = _REGISTRY.get(agent_config.name)
        if handler is None:
            available = ", ".join(sorted(_REGISTRY))
            raise KeyError(f"Agent inconnu: {agent_config.name}. Agents disponibles: {available}")
        results.append(handler(dataset, agent_config.params))
    return results


@register_agent("summary")
def summary_agent(dataset, params: dict[str, Any]) -> AgentResult:
    return AgentResult(
        name="summary",
        payload={
            "rows": int(len(dataset)),
            "columns": list(dataset.columns),
            "missing_values": dataset.isna().sum().astype(int).to_dict(),
        },
    )


@register_agent("sentiment_summary")
def sentiment_summary_agent(dataset, params: dict[str, Any]) -> AgentResult:
    column = params.get("column", "Sentiment")
    _require_column(dataset, column)
    counts = dataset[column].fillna("unknown").value_counts().to_dict()
    return AgentResult(name="sentiment_summary", payload={"column": column, "counts": counts})


@register_agent("top_values")
def top_values_agent(dataset, params: dict[str, Any]) -> AgentResult:
    column = params["column"]
    limit = int(params.get("limit", 10))
    _require_column(dataset, column)
    counts = dataset[column].fillna("unknown").value_counts().head(limit).to_dict()
    return AgentResult(name="top_values", payload={"column": column, "values": counts})


@register_agent("export")
def export_agent(dataset, params: dict[str, Any]) -> AgentResult:
    output_path = Path(params.get("path", "outputs/filtered_dataset.csv"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(output_path, index=False, encoding="utf-8")
    return AgentResult(name="export", payload={"path": str(output_path), "rows": int(len(dataset))})


def _require_column(dataset, column: str) -> None:
    if column not in dataset.columns:
        raise KeyError(f"Colonne inconnue pour l'agent: {column}")
