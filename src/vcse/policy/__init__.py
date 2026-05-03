"""Policy enforcement layer."""

from vcse.policy.actions import ALLOWED_ACTIONS, FORBIDDEN_ACTIONS
from vcse.policy.defaults import DEFAULT_POLICY
from vcse.policy.enforcer import PolicyEnforcer
from vcse.policy.loader import PolicyLoadError, load_policy
from vcse.policy.model import PolicyDecision, PolicyRule, PolicySet
from vcse.policy.rules import ExecutionProfile, ExecutionRule

# PolicyExecutionEngine, PolicyExecutionResult, PolicyExecutor are importable
# from their submodules directly; omitted here to avoid circular imports via trust layer.

__all__ = [
    "ALLOWED_ACTIONS",
    "DEFAULT_POLICY",
    "FORBIDDEN_ACTIONS",
    "ExecutionProfile",
    "ExecutionRule",
    "PolicyDecision",
    "PolicyEnforcer",
    "PolicyLoadError",
    "PolicyRule",
    "PolicySet",
    "load_policy",
]
