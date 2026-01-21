"""
Workflow Execution Engine

Direct workflow execution without code generation.
Executes visual workflow graphs created in the strategy builder.
"""

from .executor import WorkflowExecutor

__all__ = ['WorkflowExecutor']
