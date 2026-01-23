"""
LocalAgent v2.10.17 - CORE: Negotiator
🧠 SMART - Négocie avec Claude, retry intelligent, auto-split

Stratégies de négociation basées sur le type d'erreur
Utilise le learning pour améliorer les prompts
"""

import re
from typing import Dict, List, Tuple, Optional

from .constraints import validate_action, CTX_CONSTRAINTS, build_system_prompt
from .learning import (
    learn_from_error,
    learn_dodge,
    get_error_context_for_retry,
    has_learned_solution
)


# ============================================================
# NEGOTIATION STRATEGIES
# ============================================================

NEGOTIATION_STRATEGIES = {
    "truncation": {
        "action": "reduce_complexity",
        "feedback": "Response truncated. Use fewer, simpler tasks. Max 2 tasks, max 20 lines each.",
        "max_retries": 3
    },
    "parse_error": {
        "action": "simplify_json",
        "feedback": "JSON parse error. Return ONLY valid JSON. Start with { end with }. No markdown.",
        "max_retries": 3
    },
    "empty_response": {
        "action": "retry_simple",
        "feedback": "Empty response received. Please provide tasks in JSON format.",
        "max_retries": 2
    },
    "no_tasks": {
        "action": "clarify_format",
        "feedback": "No tasks found. Return: {\"tasks\": [{\"id\": \"T001\", \"type\": \"...\", ...}]}",
        "max_retries": 2
    },
    "invalid_task": {
        "action": "fix_schema",
        "feedback": "Task missing required fields. Each task needs: id, type, description",
        "max_retries": 2
    },
    "file_not_found": {
        "action": "list_available",
        "feedback": "File not found. Only reference files explicitly listed in context.",
        "max_retries": 1
    },
    "too_complex": {
        "action": "split_instruction",
        "feedback": "Instruction too complex. Will be split into smaller parts.",
        "max_retries": 0
    },
    "dodge_detected": {
        "action": "insist",
        "feedback": "Do not refuse or ask for clarification. Execute the task as specified.",
        "max_retries": 2
    }
}


# ============================================================
# AUTO-SPLIT COMPLEX INSTRUCTIONS
# ============================================================

def analyze_instruction_complexity(instruction: str) -> Dict:
    """
    Analyze if instruction is too complex and needs splitting.
    
    Returns:
        {
            "needs_split": bool,
            "complexity_score": int,
            "parts": list of sub-instructions,
            "indicators": list of complexity indicators found
        }
    """
    instruction_lower = instruction.lower()
    
    # Complexity indicators with weights
    indicators = []
    score = 0
    
    complexity_markers = [
        (r'\band\b', 1, "and"),
        (r'\bthen\b', 2, "then"),
        (r'\balso\b', 1, "also"),
        (r'\bplus\b', 1, "plus"),
        (r'\bfinally\b', 2, "finally"),
        (r'\bfirst\b', 1, "first"),
        (r'\bsecond\b', 2, "second"),
        (r'\bthird\b', 3, "third"),
        (r'\d+\.', 2, "numbered_list"),
        (r'\bafter that\b', 2, "after_that"),
        (r'\bonce done\b', 2, "once_done"),
    ]
    
    for pattern, weight, name in complexity_markers:
        if re.search(pattern, instruction_lower):
            score += weight
            indicators.append(name)
    
    # Length factor
    if len(instruction) > 500:
        score += 2
        indicators.append("long_instruction")
    if len(instruction) > 1000:
        score += 2
        indicators.append("very_long_instruction")
    
    # Needs split if score >= 4
    needs_split = score >= 4
    
    parts = []
    if needs_split:
        parts = _split_instruction(instruction)
    
    return {
        "needs_split": needs_split,
        "complexity_score": score,
        "parts": parts if parts else [instruction],
        "indicators": indicators
    }


def _split_instruction(instruction: str) -> List[str]:
    """Split complex instruction into parts."""
    parts = []
    
    # Try numbered list first (1. 2. 3.)
    numbered = re.split(r'\d+\.\s*', instruction)
    if len(numbered) > 1:
        parts = [p.strip() for p in numbered if p.strip()]
        if len(parts) > 1:
            return parts[:5]  # Max 5 parts
    
    # Try "then" splits
    if " then " in instruction.lower():
        parts = re.split(r'\s+then\s+', instruction, flags=re.IGNORECASE)
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()][:5]
    
    # Try "and" splits (less aggressive)
    if " and " in instruction.lower() and len(instruction) > 200:
        parts = re.split(r'\s+and\s+', instruction, flags=re.IGNORECASE)
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()][:5]
    
    return [instruction]


# ============================================================
# NEGOTIATION FEEDBACK
# ============================================================

def get_negotiation_feedback(error_type: str, context: Dict = None) -> str:
    """
    Get feedback message for negotiation based on error type.
    
    Args:
        error_type: Type of error encountered
        context: Additional context (project name, error details, etc.)
    
    Returns:
        Feedback string to include in retry prompt
    """
    strategy = NEGOTIATION_STRATEGIES.get(error_type, {})
    feedback = strategy.get("feedback", f"Error: {error_type}. Please retry.")
    
    # Add learned context if available
    if context and context.get("project"):
        learned = get_error_context_for_retry(context["project"])
        if learned:
            feedback = f"{feedback}\n\n{learned}"
    
    # Add specific solution if known
    if context and context.get("project"):
        solution = has_learned_solution(context["project"], error_type)
        if solution:
            feedback = f"{feedback}\n\nKnown fix: {solution}"
    
    return feedback


def should_retry(error_type: str, retry_count: int) -> bool:
    """Check if should retry based on error type and retry count."""
    strategy = NEGOTIATION_STRATEGIES.get(error_type, {"max_retries": 1})
    return retry_count < strategy.get("max_retries", 1)


def get_retry_action(error_type: str) -> str:
    """Get action to take for retry."""
    strategy = NEGOTIATION_STRATEGIES.get(error_type, {})
    return strategy.get("action", "retry_simple")


# ============================================================
# DODGE DETECTION
# ============================================================

DODGE_PATTERNS = [
    (r"i (?:can't|cannot|won't|will not)", "refuses"),
    (r"i'm (?:unable|not able)", "refuses"),
    (r"could you (?:clarify|explain|provide)", "asks_clarification"),
    (r"what (?:do you mean|exactly)", "asks_clarification"),
    (r"i (?:don't have|lack) (?:access|information)", "claims_limitation"),
    (r"i'm not sure what", "claims_uncertainty"),
    (r"please (?:provide|specify|clarify)", "asks_clarification"),
    (r"it's not (?:clear|possible)", "deflects"),
]


def detect_dodge(response: str) -> Optional[Tuple[str, str]]:
    """
    Detect if Claude is trying to dodge the task.
    
    Returns:
        (dodge_type, matched_text) or None
    """
    response_lower = response.lower()
    
    for pattern, dodge_type in DODGE_PATTERNS:
        match = re.search(pattern, response_lower)
        if match:
            return (dodge_type, match.group(0))
    
    return None


# ============================================================
# MAIN NEGOTIATION FLOW
# ============================================================

def negotiate_request(
    project: str,
    instruction: str,
    call_claude_fn,
    context: str = "",
    max_retries: int = 3
) -> Tuple[bool, Dict]:
    """
    Main negotiation flow with Claude.
    
    Args:
        project: Project name
        instruction: User instruction
        call_claude_fn: Function to call Claude API
        context: Additional context for Claude
        max_retries: Maximum retry attempts
    
    Returns:
        (success, result_dict)
        result_dict contains: tasks, error, raw_response, attempts
    """
    print(f"🔄 NEGOTIATOR: Starting for project {project}")
    
    # Check instruction complexity
    complexity = analyze_instruction_complexity(instruction)
    print(f"   Complexity score: {complexity['complexity_score']}")
    
    if complexity["needs_split"]:
        print(f"   ⚠️ Too complex - needs split into {len(complexity['parts'])} parts")
        return False, {
            "error": "too_complex",
            "split_required": True,
            "parts": complexity["parts"],
            "suggestion": f"Split into {len(complexity['parts'])} parts"
        }
    
    # Build system prompt FROM CONSTRAINTS + LEARNED ERRORS (not hardcoded)
    system_prompt = build_system_prompt(project)
    
    # Get additional learned errors context
    error_context = get_error_context_for_retry(project)
    full_context = f"SYSTEM:\n{system_prompt}\n\n{context}"
    if error_context:
        full_context += f"\n\n{error_context}"
    
    attempts = []
    retry_count = 0
    
    while retry_count <= max_retries:
        print(f"   📡 Attempt {retry_count + 1}/{max_retries + 1}")
        
        # Build prompt with feedback from previous attempts
        prompt = instruction
        if attempts:
            last_error = attempts[-1].get("error_type", "unknown")
            feedback = get_negotiation_feedback(last_error, {"project": project})
            prompt = f"{instruction}\n\nPREVIOUS_ERROR: {last_error}\nREQUIRED_FIX: {feedback}"
            print(f"      Adding feedback for: {last_error}")
        
        # Call Claude
        result = call_claude_fn(prompt, full_context)
        
        attempt = {
            "retry": retry_count,
            "prompt_length": len(prompt),
            "timestamp": None  # Would be set by caller
        }
        
        if not result.get("success"):
            error_type = "api_error"
            attempt["error_type"] = error_type
            attempt["error"] = result.get("error", "Unknown API error")
            attempts.append(attempt)
            
            learn_from_error(project, error_type, result.get("error", ""))
            
            if not should_retry(error_type, retry_count):
                break
            retry_count += 1
            continue
        
        response = result.get("response", "")
        attempt["response_length"] = len(response)
        
        # Detect dodge
        dodge = detect_dodge(response)
        if dodge:
            dodge_type, dodge_text = dodge
            print(f"      ⚠️ Dodge detected: {dodge_type}")
            attempt["error_type"] = "dodge_detected"
            attempt["dodge_type"] = dodge_type
            attempts.append(attempt)
            
            learn_dodge(project, dodge_type, dodge_text)
            
            if not should_retry("dodge_detected", retry_count):
                break
            retry_count += 1
            continue
        
        # Validate response
        validation = validate_response(response)
        print(f"      Validation: {'✅ valid' if validation['valid'] else '❌ ' + validation.get('error_type', 'unknown')}")
        
        if not validation["valid"]:
            error_type = validation["error_type"]
            print(f"      Error: {validation.get('detail', '')[:100]}")
            attempt["error_type"] = error_type
            attempt["error"] = validation.get("detail", "")
            attempts.append(attempt)
            
            learn_from_error(project, error_type, validation.get("detail", ""), 
                           {"instruction": instruction[:200]})
            
            if not should_retry(error_type, retry_count):
                print(f"      Max retries for {error_type} reached")
                break
            retry_count += 1
            continue
        
        # Success!
        print(f"      ✅ Success: {len(validation['tasks'])} tasks validated")
        attempt["success"] = True
        attempts.append(attempt)
        
        return True, {
            "tasks": validation["tasks"],
            "raw_response": response,
            "attempts": attempts,
            "usage": result.get("usage", {})
        }
    
    # All retries failed
    return False, {
        "error": attempts[-1].get("error_type", "unknown") if attempts else "no_attempts",
        "detail": attempts[-1].get("error", "") if attempts else "",
        "attempts": attempts
    }


# ============================================================
# RESPONSE VALIDATION
# ============================================================

def validate_response(response: str) -> Dict:
    """
    Validate Claude's response.
    
    Returns:
        {
            "valid": bool,
            "tasks": list (if valid),
            "error_type": str (if invalid),
            "detail": str (if invalid)
        }
    """
    import json
    
    # Empty check
    if not response or not response.strip():
        return {"valid": False, "error_type": "empty_response", "detail": "Empty response"}
    
    # Strip markdown (CTX002)
    text = response.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1].strip()
    
    # JSON structure check
    if not text.startswith("{"):
        return {
            "valid": False,
            "error_type": "parse_error",
            "detail": f"Response doesn't start with {{: {text[:50]}..."
        }
    
    if not text.endswith("}"):
        return {
            "valid": False,
            "error_type": "truncation",
            "detail": f"Response truncated, ends with: ...{text[-50:]}"
        }
    
    # Parse JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "error_type": "parse_error",
            "detail": f"JSON parse error: {str(e)}"
        }
    
    # Check for error response from Claude
    if "error" in data:
        return {
            "valid": False,
            "error_type": "claude_error",
            "detail": data.get("error"),
            "suggestion": data.get("suggestion")
        }
    
    # Check for tasks
    tasks = data.get("tasks", [])
    if not tasks:
        return {
            "valid": False,
            "error_type": "no_tasks",
            "detail": "Response contains no tasks"
        }
    
    # Validate each task
    for i, task in enumerate(tasks):
        required = ["id", "type", "description"]
        missing = [f for f in required if f not in task]
        if missing:
            return {
                "valid": False,
                "error_type": "invalid_task",
                "detail": f"Task {i+1} missing fields: {missing}"
            }
        
        # CRITICAL: create_file MUST have content
        task_type = task.get("type", "")
        if task_type in ("create_file", "file", "create", "write_file"):
            filename = task.get("file_path") or task.get("filename") or task.get("file") or task.get("path")
            content = task.get("content", "") or task.get("code", "") or task.get("data", "")
            if not filename:
                return {
                    "valid": False,
                    "error_type": "missing_filename",
                    "detail": f"Task {i+1} (create_file) missing file_path/filename"
                }
            if not content or len(content) < 20:
                return {
                    "valid": False,
                    "error_type": "missing_content",
                    "detail": f"Task {i+1} (create_file) missing or empty content field (need complete file)"
                }
    
    # Check task count (CTX003)
    if len(tasks) > 3:
        return {
            "valid": False,
            "error_type": "too_many_tasks",
            "detail": f"Too many tasks: {len(tasks)} (max 3)"
        }
    
    return {"valid": True, "tasks": tasks}
