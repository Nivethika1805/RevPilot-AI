import re
from typing import List, Dict, Any, Optional

OBJECTION_PATTERNS = {
    "pricing": [
        r"(price|pricing|expensive|budget|cost|discount|rate|roi|quote|afford|commercials?)",
        r"(too high|out of our range|cost prohibitive|reduce the fee)"
    ],
    "product_technical": [
        r"(security|compliance|soc2|hipaa|latency|integration|api|scalability|performance|feature gap)",
        r"(missing feature|cannot support|doesn't integrate|limitation|technical hurdle)"
    ],
    "implementation": [
        r"(timeline|onboarding|resources?|bandwidth|deployment|delay|training|go-live)",
        r"(tight deadline|delayed rollout|capacity constraints)"
    ],
    "contract_legal": [
        r"(legal|terms|redline|indemnity|sla|clause|procurement|msa)",
        r"(waiting on legal|procurement approval|vendor form)"
    ]
}

COMPETITOR_PATTERNS = [
    r"\b(Gong|Chorus|Salesforce|Hubspot|Clari|Salesloft|Outreach|LegacyCRM|CompeteCorp|AlphaRev)\b"
]

COMMITMENT_PATTERNS = [
    r"(will send|promise to|agreed to follow up|schedule a follow up|share the proposal|deliver by|circle back|next step is|action item)",
    r"(send over the updated|provide the revised|set up a demo)"
]

SENTIMENT_PATTERNS = {
    "negative": [
        r"(frustrated|disappointed|concerned|unacceptable|skeptical|delaying|hesitant|blocked|risk|unhappy)",
        r"(not satisfied|pushing back|worried about)"
    ],
    "positive": [
        r"(excited|impressed|love the|great progress|approved|looks solid|aligned|ready to move|happy with)",
        r"(strong interest|confident|forward with)"
    ]
}

def extract_evidence_and_findings(
    raw_text: str,
    source_record_ref: str,
    occurred_at
) -> Dict[str, Any]:
    """
    Deterministic rules-based extractor for conversation intelligence.
    Extracts objections, questions, competitor mentions, commitments, and sentiment basis.
    Every finding includes the exact text span and character offsets.
    """
    lines = raw_text.splitlines()
    excerpts = []
    findings = []
    
    # Analyze lines and paragraphs
    for line_idx, line in enumerate(lines, 1):
        clean_line = line.strip()
        if not clean_line or len(clean_line) < 10:
            continue
            
        line_start = raw_text.find(clean_line)
        line_end = line_start + len(clean_line) if line_start != -1 else None

        # Check for objections
        for obj_cat, patterns in OBJECTION_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, clean_line, re.IGNORECASE):
                    source_ref = f"{source_record_ref}#L{line_idx}"
                    excerpt_obj = {
                        "source_type": "conversation_line",
                        "source_ref": source_ref,
                        "excerpt_text": clean_line,
                        "start_offset": line_start,
                        "end_offset": line_end,
                        "occurred_at": occurred_at,
                        "extractor": "rules"
                    }
                    excerpts.append(excerpt_obj)
                    findings.append({
                        "kind": "objection",
                        "label": f"Unresolved {obj_cat.replace('_', ' ').title()} Objection",
                        "status": "open",
                        "source_ref": source_ref,
                        "confidence": 0.95
                    })
                    break

        # Check for competitor mentions
        for pat in COMPETITOR_PATTERNS:
            m = re.search(pat, clean_line, re.IGNORECASE)
            if m:
                competitor = m.group(1)
                source_ref = f"{source_record_ref}#L{line_idx}"
                excerpts.append({
                    "source_type": "conversation_line",
                    "source_ref": source_ref,
                    "excerpt_text": clean_line,
                    "start_offset": line_start,
                    "end_offset": line_end,
                    "occurred_at": occurred_at,
                    "extractor": "rules"
                })
                findings.append({
                    "kind": "competitor_mention",
                    "label": f"Competitor Mentioned: {competitor}",
                    "status": "open",
                    "source_ref": source_ref,
                    "confidence": 1.0
                })
                break

        # Check for follow-up commitments
        for pat in COMMITMENT_PATTERNS:
            if re.search(pat, clean_line, re.IGNORECASE):
                source_ref = f"{source_record_ref}#L{line_idx}"
                excerpts.append({
                    "source_type": "conversation_line",
                    "source_ref": source_ref,
                    "excerpt_text": clean_line,
                    "start_offset": line_start,
                    "end_offset": line_end,
                    "occurred_at": occurred_at,
                    "extractor": "rules"
                })
                findings.append({
                    "kind": "follow_up_commitment",
                    "label": "Documented Follow-up Commitment",
                    "status": "open",
                    "source_ref": source_ref,
                    "confidence": 0.90
                })
                break

        # Check for unresolved questions
        if "?" in clean_line and ("how" in clean_line.lower() or "can you" in clean_line.lower() or "what if" in clean_line.lower()):
            source_ref = f"{source_record_ref}#L{line_idx}"
            excerpts.append({
                "source_type": "conversation_line",
                "source_ref": source_ref,
                "excerpt_text": clean_line,
                "start_offset": line_start,
                "end_offset": line_end,
                "occurred_at": occurred_at,
                "extractor": "rules"
            })
            findings.append({
                "kind": "unresolved_question",
                "label": "Unresolved Customer Question",
                "status": "open",
                "source_ref": source_ref,
                "confidence": 0.85
            })

    # Sentiment extraction
    sentiment_label = "neutral"
    sentiment_basis = None
    neg_count = 0
    pos_count = 0
    neg_basis = []
    pos_basis = []

    for clean_line in lines:
        for pat in SENTIMENT_PATTERNS["negative"]:
            if re.search(pat, clean_line, re.IGNORECASE):
                neg_count += 1
                neg_basis.append(clean_line.strip())
        for pat in SENTIMENT_PATTERNS["positive"]:
            if re.search(pat, clean_line, re.IGNORECASE):
                pos_count += 1
                pos_basis.append(clean_line.strip())

    if neg_count > pos_count and neg_count > 0:
        sentiment_label = "negative"
        sentiment_basis = " | ".join(neg_basis[:2])
    elif pos_count > neg_count and pos_count > 0:
        sentiment_label = "positive"
        sentiment_basis = " | ".join(pos_basis[:2])
    elif len(raw_text.strip()) < 40:
        sentiment_label = "not_enough_evidence"
        sentiment_basis = "Insufficient conversational text to establish customer sentiment."
    else:
        sentiment_label = "neutral"
        sentiment_basis = "Balanced tone across discussion points."

    return {
        "excerpts": excerpts,
        "findings": findings,
        "sentiment_label": sentiment_label,
        "sentiment_basis": sentiment_basis
    }
