"""Deterministic SAP BRIM topic classifier for answers shared to an organisation's knowledge hub.

No LLM call: keyword rules on the question and the answer (docs/ORGANISATION_PORTAL.md, "Categories").
Order: troubleshooting -> integration -> highest-scoring component (cc, ci, som, fica) ->
architecture/configuration -> general. The question decides troubleshooting, integration and
architecture; the answer only adds weight to the component scores, because answers routinely mention
errors and neighbouring components in passing.
"""

import re
from typing import Dict, List, Pattern, Tuple

CATEGORIES: Tuple[Tuple[str, str], ...] = (
    ("cc", "Convergent Charging (CC)"),
    ("ci", "Convergent Invoicing (CI)"),
    ("som", "Subscription Order Management (SOM)"),
    ("fica", "FI-CA"),
    ("integration", "SAP BRIM Integration"),
    ("troubleshooting", "Troubleshooting"),
    ("architecture", "Architecture and Configuration"),
    ("general", "General SAP"),
)
CATEGORY_LABELS: Dict[str, str] = dict(CATEGORIES)
CATEGORY_KEYS: Tuple[str, ...] = tuple(key for key, _ in CATEGORIES)
DEFAULT_CATEGORY = "general"


def _patterns(*expressions: str) -> List[Pattern]:
    return [re.compile(expression, re.IGNORECASE) for expression in expressions]


_OUTCOME = r"(?:generated|created|posted|triggered|billed|invoiced|processed|updated|transferred|picked\s+up)"
TROUBLESHOOTING = _patterns(r"\berrors?\b", r"\bfail(?:s|ed|ing|ure|ures)?\b", r"\bissues?\b",
                            r"\bnot\s+(?:being\s+|been\s+|getting\s+)?" + _OUTCOME + r"\b",
                            r"\bno\s+(?:[\w-]+\s+){0,3}(?:was|were|is|are|has\s+been|have\s+been|got)\s+" + _OUTCOME + r"\b",
                            r"\b(?:did|does|do|is|was|were|has|have)\s*n[o']?t\s+(?:been\s+|get\s+)?"
                            r"(?:generate|create|post|trigger|bill|invoice|process|update|transfer|work|run)\w*\b",
                            # "Why wasn't the invoice posted", "isn't the order being transferred"
                            r"\b(?:was|were|is|are|has|have)n['’]?t\b(?:\s+[\w-]+){0,4}?\s+(?:being\s+|been\s+)?"
                            + _OUTCOME + r"\b",
                            r"\bmissing\b", r"\bwhat\s+should\s+(?:i|we)\s+check\b",
                            r"\bhow\s+(?:do|can|should)\s+(?:i|we)\s+(?:fix|resolve|solve|debug)\b",
                            r"\btroubleshoot\w*\b", r"\b(?:short\s+)?dumps?\b", r"\bstuck\b",
                            r"\breprocess(?:es|ed|ing)?\b")
INTEGRATION = _patterns(r"\bintegrat(?:e|es|ed|ion|ions|ing)\b", r"\binterfaces?\b", r"\bend[\s-]+to[\s-]+end\b",
                        r"\brfcs?\b", r"\bidocs?\b", r"\breplicat(?:e|es|ed|ion|ing)\b")
ARCHITECTURE = _patterns(r"\bconfigur(?:e|es|ed|ing|ation|ations)\b", r"\bcustomi[sz]ing\b", r"\bspro\b",
                         r"\barchitecture\b", r"\bdesign(?:s|ed|ing)?\b", r"\bset\s*-?\s*up\b", r"\bsetups?\b")

# The component's own name: two or more named components make an integration question.
COMPONENT_NAMES: Dict[str, List[Pattern]] = {
    "cc": _patterns(r"\bconvergent\s+charging\b", r"\bsap\s+cc\b", r"\bcc\b"),
    "ci": _patterns(r"\bconvergent\s+invoicing\b", r"\bsap\s+ci\b", r"\bci\b"),
    "som": _patterns(r"\bsubscription\s+order\s+management\b", r"\bsom\b"),
    "fica": _patterns(r"\bfi[\s-]?ca\b", r"\bcontract\s+accounting\b"),
}
# Further terms that point at a component without naming it.
COMPONENT_TERMS: Dict[str, List[Pattern]] = {
    "cc": _patterns(r"\bcharging\b", r"\brating\b", r"\bcharge\s+plans?\b", r"\bprice\s+plans?\b",
                    r"\ballowances?\b", r"\brefills?\b", r"\bpricing\s+catalog"),
    "ci": _patterns(r"\binvoicing\b", r"\bbillable\s+items?\b", r"(?-i:\bBITs?\b)", r"\bconsumption\s+items?\b",
                    r"\bbilling\s+documents?\b", r"\binvoice\s+documents?\b", r"\bbilling\s+run\b"),
    "som": _patterns(r"\bsubscription\s+orders?\b", r"\bsubscriptions?\b", r"\bsolution\s+quotes?\b",
                     r"\bproduct\s+configuration\b", r"\bprovider\s+order\b"),
    "fica": _patterns(r"\bcontract\s+accounts?\b", r"\bprovider\s+contracts?\b", r"\bdunning\b",
                      r"\bpayment\s+runs?\b", r"\bclearing\b", r"\bopen\s+items?\b", r"\bpostings?\b"),
}
COMPONENT_ORDER = ("cc", "ci", "som", "fica")
QUESTION_WEIGHT = 3


def _any(patterns: List[Pattern], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _hits(patterns: List[Pattern], text: str) -> int:
    return sum(len(pattern.findall(text)) for pattern in patterns)


def named_components(text: str) -> List[str]:
    return [key for key in COMPONENT_ORDER if _any(COMPONENT_NAMES[key], text)]


def categorise(question: str, answer: str = "") -> str:
    question = question or ""
    answer = answer or ""
    if _any(TROUBLESHOOTING, question):
        return "troubleshooting"
    if _any(INTEGRATION, question) or len(named_components(question)) >= 2:
        return "integration"
    scores = {}
    for key in COMPONENT_ORDER:
        patterns = COMPONENT_NAMES[key] + COMPONENT_TERMS[key]
        scores[key] = QUESTION_WEIGHT * _hits(patterns, question) + _hits(patterns, answer)
    best = max(COMPONENT_ORDER, key=lambda key: (scores[key], -COMPONENT_ORDER.index(key)))
    if scores[best] > 0:
        return best
    if _any(ARCHITECTURE, question) or _any(ARCHITECTURE, answer):
        return "architecture"
    return DEFAULT_CATEGORY


def category_label(key: str) -> str:
    return CATEGORY_LABELS.get(key, CATEGORY_LABELS[DEFAULT_CATEGORY])
