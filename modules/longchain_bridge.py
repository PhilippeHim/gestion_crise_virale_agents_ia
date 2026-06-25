from __future__ import annotations

from typing import Any

from datathon_pipeline.agents import run_agents
from datathon_pipeline.config import AgentConfig


def build_longchain_agent_action(agent_name: str, params: dict[str, Any] | None = None):
    """Wrap a configured pipeline agent as a longchain AgentAction.

    The longchain Player must contain a pandas DataFrame in
    `player.plugin_state["datathon_pipeline"]["dataset"]`.
    """
    try:
        from longchain.core.dataclasses import Message, PathResult
        from longchain.impl.agentaction.arbitrary import ArbitraryAgentAction
    except ModuleNotFoundError as exc:
        raise RuntimeError("longchain doit etre installe pour utiliser ce pont.") from exc

    async def _run(path, player, player_actions):
        state = player.plugin_state.setdefault("datathon_pipeline", {})
        dataset = state.get("dataset")
        if dataset is None:
            raise RuntimeError(
                "Aucun dataset trouve dans player.plugin_state['datathon_pipeline']['dataset']."
            )

        result = run_agents(dataset, [AgentConfig(name=agent_name, params=params or {})])[0]
        state.setdefault("agent_results", []).append(result.payload)
        return PathResult(
            next_action="path",
            new_path_id=None,
            messages=[
                Message(
                    text=f"Agent {agent_name} execute: {result.payload}",
                    interaction_id=player.interaction_id,
                )
            ],
        )

    return ArbitraryAgentAction(_run)
