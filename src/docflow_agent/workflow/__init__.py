"""Workflow layer for stateful execution orchestration.

Workflows own request-scoped state, artifact references, HITL control flow,
and multi-step execution order. They do not own business rules and they do
not know about the bootstrap container.
"""
