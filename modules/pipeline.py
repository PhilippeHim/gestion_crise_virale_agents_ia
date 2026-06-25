from __future__ import annotations

from datathon_pipeline.agents import AgentResult, run_agents
from datathon_pipeline.config import PipelineConfig
from datathon_pipeline.dataset import apply_filters, load_dataset


def run_pipeline(config: PipelineConfig) -> tuple[object, list[AgentResult]]:
    dataset = load_dataset(config.input.path, sheet_name=config.input.sheet_name)
    filtered_dataset = apply_filters(dataset, config.filters)
    results = run_agents(filtered_dataset, config.agents)
    return filtered_dataset, results
