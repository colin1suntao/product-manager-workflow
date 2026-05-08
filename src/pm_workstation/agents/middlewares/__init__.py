"""中间件模块

提供可组合的中间件链，处理横切关注点。
"""

from pm_workstation.agents.middlewares.audit import AuditMiddleware
from pm_workstation.agents.middlewares.base import Middleware, MiddlewareChain, MiddlewareState
from pm_workstation.agents.middlewares.context import ContextMiddleware
from pm_workstation.agents.middlewares.error_handling import ErrorHandlingMiddleware
from pm_workstation.agents.middlewares.state_persistence import StatePersistenceMiddleware
from pm_workstation.agents.middlewares.summarization import SummarizationMiddleware

__all__ = [
    "AuditMiddleware",
    "ContextMiddleware",
    "ErrorHandlingMiddleware",
    "Middleware",
    "MiddlewareChain",
    "MiddlewareState",
    "StatePersistenceMiddleware",
    "SummarizationMiddleware",
]
