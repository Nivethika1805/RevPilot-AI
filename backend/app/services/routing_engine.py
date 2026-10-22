from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

def match_conditions(conditions: Dict[str, Any], context: Dict[str, Any]) -> tuple[bool, int]:
    """
    Evaluates rule conditions against conversation/deal context.
    Returns (is_match, specificity).
    Specificity = number of conditions explicitly tested and matched.
    """
    if not conditions:
        return False, 0

    specificity = 0
    for key, expected_val in conditions.items():
        specificity += 1
        actual_val = context.get(key)
        
        if isinstance(expected_val, list):
            # If expected is a list, context value must be in list or vice versa
            if isinstance(actual_val, list):
                if not any(item in expected_val for item in actual_val):
                    return False, specificity
            else:
                if actual_val not in expected_val:
                    return False, specificity
        elif isinstance(expected_val, bool):
            if bool(actual_val) != expected_val:
                return False, specificity
        elif isinstance(expected_val, (int, float)):
            if actual_val != expected_val:
                return False, specificity
        elif isinstance(expected_val, str):
            if str(actual_val).lower() != expected_val.lower():
                return False, specificity
        else:
            if actual_val != expected_val:
                return False, specificity

    return True, specificity

def evaluate_routing(
    conversation_context: Dict[str, Any],
    rules: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Pure deterministic routing evaluation.
    Precedence:
    1. lowest priority_order wins
    2. tie -> higher specificity wins
    3. tie -> if recommend same owner, that owner wins; if different owners, UNASSIGNED REVIEW QUEUE.
    """
    rules_evaluated = []
    matched_rules = []

    for rule in sorted(rules, key=lambda r: (r.get("priority_order", 999), -r.get("specificity", 0))):
        if not rule.get("enabled", True):
            continue
            
        conditions = rule.get("conditions", {})
        is_match, spec = match_conditions(conditions, conversation_context)
        
        eval_record = {
            "rule_id": rule.get("id"),
            "rule_name": rule.get("name"),
            "priority_order": rule.get("priority_order"),
            "specificity": spec,
            "target_owner_id": rule.get("target_owner_user_id"),
            "target_team_id": rule.get("target_team_id"),
            "priority_outcome": rule.get("priority_outcome", "medium"),
            "matched": is_match
        }
        rules_evaluated.append(eval_record)
        
        if is_match:
            matched_rules.append(eval_record)

    if not matched_rules:
        return {
            "status": "unassigned_review",
            "winning_rule_id": None,
            "recommended_owner_id": None,
            "alternative_owner_id": None,
            "priority": "medium",
            "reason": "No active routing rule matched the conversation context (missing or ambiguous ownership). Routed to Unassigned Review Queue.",
            "rules_evaluated": rules_evaluated,
            "matched_rule_ids": []
        }

    # Sort matched rules: (priority_order ASC, specificity DESC)
    matched_rules.sort(key=lambda r: (r["priority_order"], -r["specificity"]))
    best = matched_rules[0]

    # Check for tie at top
    tied = [
        r for r in matched_rules 
        if r["priority_order"] == best["priority_order"] and r["specificity"] == best["specificity"]
    ]

    if len(tied) > 1:
        # Check if they recommend the same owner
        owners = set(r["target_owner_id"] for r in tied)
        if len(owners) > 1:
            # Different owners! Must enter unassigned review queue
            return {
                "status": "unassigned_review",
                "winning_rule_id": None,
                "recommended_owner_id": None,
                "alternative_owner_id": None,
                "priority": "high",
                "reason": f"Routing Conflict: Multiple rules ({', '.join(r['rule_name'] for r in tied)}) matched with identical precedence ({best['priority_order']}) and specificity ({best['specificity']}) but recommend conflicting owners. Routed to Unassigned Review Queue.",
                "rules_evaluated": rules_evaluated,
                "matched_rule_ids": [r["rule_id"] for r in matched_rules]
            }

    winning_rule = best
    alternative = matched_rules[1] if len(matched_rules) > 1 else None

    reason = f"Routed via rule '{winning_rule['rule_name']}' (precedence: {winning_rule['priority_order']}, specificity: {winning_rule['specificity']})."
    if alternative:
        reason += f" Rejected alternative '{alternative['rule_name']}' due to lower precedence order ({alternative['priority_order']} vs {winning_rule['priority_order']}) or lower specificity ({alternative['specificity']} vs {winning_rule['specificity']})."

    return {
        "status": "recommended",
        "winning_rule_id": winning_rule["rule_id"],
        "recommended_owner_id": winning_rule["target_owner_id"],
        "alternative_owner_id": alternative["target_owner_id"] if alternative else None,
        "priority": winning_rule["priority_outcome"],
        "reason": reason,
        "rules_evaluated": rules_evaluated,
        "matched_rule_ids": [r["rule_id"] for r in matched_rules]
    }
