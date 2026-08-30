from typing import TypedDict, List, Dict, Any, Optional


class RepoPilotState(TypedDict):
    """
    Shared state passed between LangGraph agents.
    """

    repo_id: str
    question: str
    route: Optional[str]

    contexts: List[Dict[str, Any]]

    # Repository-wide deterministic security scan results.
    security_findings: List[Dict[str, Any]]
    security_scan_summary: Optional[Dict[str, Any]]

    answer: Optional[str]
    verified: Optional[bool]
    verifier_notes: Optional[str]
    steps: List[str]