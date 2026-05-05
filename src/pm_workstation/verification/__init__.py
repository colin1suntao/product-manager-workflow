"""校验模块"""

from pm_workstation.verification.autofixer import AutoFixer, FixAction, FixResult
from pm_workstation.verification.consistency_checker import (
    ConsistencyCheckResult,
    ConsistencyChecker,
    ConsistencyIssue,
)
from pm_workstation.verification.document_models import (
    DocIssueSeverity,
    DocIssueType,
    DocumentIssue,
    DocumentVerificationReport,
    FormatCheckResult,
    StructureCheckResult,
)
from pm_workstation.verification.document_verifier import (
    DocumentFormatChecker,
    DocumentStructureChecker,
    DocumentVerifier,
)
from pm_workstation.verification.issue_reporter import (
    CategorizedIssue,
    IssueReporter,
    IssueSummary,
    VerificationReport,
)
from pm_workstation.verification.prototype_verifier import (
    InteractionVerifier,
    PageCoverageChecker,
    PrototypeVerifier,
)
from pm_workstation.verification.verification_models import (
    CoverageResult,
    InteractionCheckResult,
    IssueSeverity,
    IssueType,
    PrototypeVerificationReport,
    VerificationIssue,
)

__all__ = [
    "AutoFixer",
    "CategorizedIssue",
    "ConsistencyCheckResult",
    "ConsistencyChecker",
    "ConsistencyIssue",
    "CoverageResult",
    "DocIssueSeverity",
    "DocIssueType",
    "DocumentFormatChecker",
    "DocumentIssue",
    "DocumentStructureChecker",
    "DocumentVerificationReport",
    "DocumentVerifier",
    "FixAction",
    "FixResult",
    "FormatCheckResult",
    "InteractionCheckResult",
    "InteractionVerifier",
    "IssueReporter",
    "IssueSeverity",
    "IssueSummary",
    "IssueType",
    "PageCoverageChecker",
    "PrototypeVerificationReport",
    "PrototypeVerifier",
    "StructureCheckResult",
    "VerificationIssue",
    "VerificationReport",
]
