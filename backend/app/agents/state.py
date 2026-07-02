from typing import TypedDict, List, Dict, Any, Optional


class RepoPilotState(TypedDict):
    """
    Shared state passed between LangGraph agents.
    """

    repo_id: str
    question: str
    route: Optional[str]
    contexts: List[Dict[str, Any]]
    answer: Optional[str]
    verified: Optional[bool]
    verifier_notes: Optional[str]
    steps: List[str]