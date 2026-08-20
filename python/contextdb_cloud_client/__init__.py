"""contextdb-cloud-client — remote client for the ContextDB Cloud data plane.

Hosted alpha. Not production-ready. The API key is a server credential;
never ship it in a browser or client-side code.
"""

from contextdb_cloud_client.client import CloudClient
from contextdb_cloud_client.local import LocalClient
from contextdb_cloud_client.types import (
    ActionDecision,
    ActionOutcome,
    ApiError,
    ConsistencyToken,
    EpistemicSource,
    ExecutionReceipt,
    ExecutionReceiptResponse,
    ForgetMode,
    ForgetResponse,
    FormationCandidate,
    FormationMode,
    FormationResponse,
    FormationStatus,
    Health,
    Memory,
    PolicyAlignment,
    ReadConsistency,
    Ready,
    RecallResult,
    ReceiptStatus,
)

__version__ = "0.1.0a1"

__all__ = [
    "ActionDecision",
    "ActionOutcome",
    "ApiError",
    "CloudClient",
    "ConsistencyToken",
    "EpistemicSource",
    "ExecutionReceipt",
    "ExecutionReceiptResponse",
    "ForgetMode",
    "ForgetResponse",
    "FormationCandidate",
    "FormationMode",
    "FormationResponse",
    "FormationStatus",
    "Health",
    "LocalClient",
    "Memory",
    "PolicyAlignment",
    "ReadConsistency",
    "Ready",
    "RecallResult",
    "ReceiptStatus",
    "__version__",
]
