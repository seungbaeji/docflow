from __future__ import annotations

from docflow_agent.bootstrap import AppContainer
from docflow_agent.workflow.process import invoke_workflow
from docflow_agent.workflow.process.factory import create_workflow
from docflow_agent.workflow.state import HumanDecision, WorkflowState


def process_request(
    *,
    container: AppContainer,
    user_input: str,
    human_decisions: list[HumanDecision] | None,
) -> WorkflowState:
    workflow = create_workflow(container)
    return invoke_workflow(
        user_input=user_input,
        human_decisions=human_decisions,
        workflow=workflow,
    )
