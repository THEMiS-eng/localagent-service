"""
LocalAgent - CORE: Negotiator
🧠 SMART - Négocie avec Claude, retry intelligent, auto-split

Stratégies de négociation basées sur le type d'erreur
Utilise le learning pour améliorer les prompts
Valide les outputs contre les contraintes des skills
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
# SKILL CONSTRAINT VALIDATORS
# ============================================================

SKILL_CONSTRAINT_VALIDATORS = {
    # Generic validators that can apply to multiple skills
    "currency_stated": {
        "patterns": [
            r"(?:USD|EUR|GBP|CHF|\$|€|£)\s*[\d,]+",
            r"[\d,]+\s*(?:USD|EUR|GBP|CHF|dollars|euros|pounds)",
            r"\[currency\]",  # Template placeholder is OK
        ],
        "error": "Currency must be clearly stated for all amounts",
        "severity": "high"
    },
    "vat_treatment": {
        "patterns": [
            r"(?:VAT|tax|excluding|including|ex\.|inc\.)",
            r"(?:net|gross)",
            r"\bVAT\b.*(?:included|excluded|exempt)",
        ],
        "error": "VAT/tax treatment must be specified",
        "severity": "medium"
    },
    "interest_separate": {
        "patterns": [
            r"(?:interest|financing)",
            r"(?:interest rate|interest calculation)",
        ],
        "error": "Interest calculations should be shown separately",
        "severity": "low",
        "check_if_mentioned": ["interest", "financing costs"]
    },
    "mitigation_addressed": {
        "patterns": [
            r"mitigation",
            r"avoided|unavoidable",
            r"reasonable steps",
        ],
        "error": "Mitigation must be addressed in damages analysis",
        "severity": "medium"
    },
    "causation_established": {
        "patterns": [
            r"caus(?:ed?|ation|al)",
            r"result(?:ing|ed) (?:from|in)",
            r"(?:due to|because of|arising from)",
            r"(?:attributable|linked) to",
        ],
        "error": "Causation must be established for each head of claim",
        "severity": "high"
    },
    "assumptions_stated": {
        "patterns": [
            r"assum(?:e|ed|ing|ption)",
            r"(?:based on|assuming that)",
            r"(?:we have assumed|it is assumed)",
        ],
        "error": "Assumptions must be clearly stated",
        "severity": "medium"
    },
    "methodology_specified": {
        "patterns": [
            r"method(?:ology)?",
            r"approach",
            r"(?:using|applying|per) (?:AACE|RICS|SCL)",
            r"(?:measured mile|Eichleay|Hudson|Emden)",
        ],
        "error": "Methodology must be specified for calculations",
        "severity": "high"
    },
    "framework_reference": {
        "patterns": [
            r"(?:AACE|RICS|SCL|FIDIC|NEC|JCT|ICC)",
            r"(?:RP \d+|29R-03|recommended practice)",
        ],
        "error": "Framework/standard reference should be included",
        "severity": "low"
    },
    "dates_specified": {
        "patterns": [
            r"\d{4}-\d{2}-\d{2}",
            r"\d{1,2}/\d{1,2}/\d{4}",
            r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
        ],
        "error": "Dates should be clearly specified",
        "severity": "low"
    },
    "period_quantified": {
        "patterns": [
            r"\d+\s*(?:days?|weeks?|months?)",
            r"(?:period|duration)\s*(?:of|:)\s*\d+",
        ],
        "error": "Time periods should be quantified",
        "severity": "medium"
    }
}

# Map skill constraints text to validators
SKILL_CONSTRAINT_MAPPING = {
    "currency clearly stated": "currency_stated",
    "vat treatment specified": "vat_treatment",
    "interest calculations separate": "interest_separate",
    "mitigation addressed": "mitigation_addressed",
    "causation established": "causation_established",
    "assumptions clearly stated": "assumptions_stated",
    "avoid double recovery": None,  # Complex - needs manual review
    "records-based where possible": None,  # Context-dependent
    "methodology": "methodology_specified",
    "framework": "framework_reference",
    "dates": "dates_specified",
    "period": "period_quantified",
}


def parse_skill_constraints(skill_body: str) -> List[str]:
    """
    Extract constraints from skill markdown body.
    
    Returns list of constraint texts.
    """
    constraints = []
    
    # Find ## Constraints section
    match = re.search(r'##\s*Constraints\s*\n([\s\S]*?)(?=\n##|\Z)', skill_body, re.IGNORECASE)
    if match:
        content = match.group(1)
        # Parse bullet points
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                constraint = line.lstrip('-*').strip()
                if constraint:
                    constraints.append(constraint.lower())
    
    return constraints


def get_validators_for_skill(skill_name: str, skill_body: str) -> List[Dict]:
    """
    Get list of validators applicable for a skill based on its constraints.
    """
    validators = []
    constraints = parse_skill_constraints(skill_body)
    
    for constraint_text in constraints:
        # Find matching validator
        for key, validator_name in SKILL_CONSTRAINT_MAPPING.items():
            if key in constraint_text and validator_name:
                validator = SKILL_CONSTRAINT_VALIDATORS.get(validator_name)
                if validator:
                    validators.append({
                        "name": validator_name,
                        "constraint_text": constraint_text,
                        **validator
                    })
                break
    
    return validators


def validate_output_against_skill(
    output: str, 
    skill_name: str, 
    skill_body: str,
    strict: bool = False
) -> Dict:
    """
    Validate LLM output against skill constraints.
    
    Args:
        output: The LLM response text
        skill_name: Name of the active skill
        skill_body: Full markdown body of the skill
        strict: If True, fail on medium severity violations too
    
    Returns:
        {
            "valid": bool,
            "violations": [{"constraint": str, "error": str, "severity": str}],
            "warnings": [{"constraint": str, "suggestion": str}],
            "score": int (0-100),
            "feedback": str (for retry prompt)
        }
    """
    validators = get_validators_for_skill(skill_name, skill_body)
    violations = []
    warnings = []
    passed = 0
    total = len(validators)
    
    if total == 0:
        return {
            "valid": True,
            "violations": [],
            "warnings": [],
            "score": 100,
            "feedback": ""
        }
    
    output_lower = output.lower()
    
    for validator in validators:
        patterns = validator.get("patterns", [])
        found = False
        
        # Check if any pattern matches
        for pattern in patterns:
            if re.search(pattern, output, re.IGNORECASE):
                found = True
                break
        
        # Special case: only check if topic is mentioned
        if not found and validator.get("check_if_mentioned"):
            topic_mentioned = any(t in output_lower for t in validator["check_if_mentioned"])
            if not topic_mentioned:
                # Topic not mentioned, so constraint doesn't apply
                found = True  # Pass by default
        
        if found:
            passed += 1
        else:
            severity = validator.get("severity", "medium")
            entry = {
                "constraint": validator.get("constraint_text", validator["name"]),
                "error": validator.get("error", "Constraint not satisfied"),
                "severity": severity
            }
            
            if severity == "high" or (strict and severity == "medium"):
                violations.append(entry)
            else:
                warnings.append({
                    "constraint": entry["constraint"],
                    "suggestion": entry["error"]
                })
    
    # Calculate score
    score = int((passed / total) * 100) if total > 0 else 100
    
    # Build feedback for retry
    feedback = ""
    if violations:
        feedback = f"Output validation failed for skill '{skill_name}':\n"
        for v in violations:
            feedback += f"- {v['error']}\n"
        feedback += "\nPlease revise to address these issues."
    
    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "score": score,
        "feedback": feedback
    }


def build_retry_prompt_with_skill_feedback(
    original_prompt: str,
    output: str,
    validation_result: Dict,
    skill_name: str
) -> str:
    """
    Build a retry prompt that includes skill constraint feedback.
    """
    feedback = validation_result.get("feedback", "")
    
    if not feedback:
        return original_prompt
    
    retry_prompt = f"""Previous response did not fully comply with {skill_name} requirements.

{feedback}

Original request:
{original_prompt}

Please provide a revised response that addresses the validation issues."""
    
    return retry_prompt


# ============================================================
# NEGOTIATION STRATEGIES
# ============================================================

NEGOTIATION_STRATEGIES = {
    "truncation": {
        "action": "reduce_complexity",
        "feedback": "Response truncated. Use fewer, simpler tasks. Max 1 task, max 15 lines content. No HTML.",
        "max_retries": 1
    },
    "parse_error": {
        "action": "simplify_json",
        "feedback": "JSON parse error. Return ONLY valid JSON. Start with { end with }. No markdown.",
        "max_retries": 1
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
    },
    # Skill constraint violations
    "skill_constraint_violation": {
        "action": "revise_with_constraints",
        "feedback": "Response does not meet skill requirements. See specific violations.",
        "max_retries": 2
    },
    # Runtime/Console errors - NEW
    "runtime_error": {
        "action": "fix_code",
        "feedback": "Code produced a runtime error when executed. Fix the error and return corrected code.",
        "max_retries": 3
    },
    "syntax_error": {
        "action": "fix_syntax",
        "feedback": "Code has syntax errors. Fix syntax and return valid code.",
        "max_retries": 3
    },
    "reference_error": {
        "action": "fix_reference",
        "feedback": "Code references undefined variable/function. Define it or fix the reference.",
        "max_retries": 2
    },
    "type_error": {
        "action": "fix_type",
        "feedback": "Type error in code. Check types and fix the operation.",
        "max_retries": 2
    },
    "console_error": {
        "action": "fix_console_error",
        "feedback": "Console caught an error during execution. Analyze and fix.",
        "max_retries": 3
    },
    "render_error": {
        "action": "fix_render",
        "feedback": "UI failed to render. Check HTML/CSS/JS syntax and component structure.",
        "max_retries": 2
    },
    "network_error": {
        "action": "handle_network",
        "feedback": "Network request failed. Check URL, handle errors gracefully.",
        "max_retries": 1
    },
    "task_mismatch": {
        "action": "fix_target_file",
        "feedback": "Task does not match instruction. If instruction says 'modify X.py', generate a task that modifies X.py directly, not a new file in Txxx/ folder. Use type 'modify_file' or 'patch_file' with the exact file path mentioned in instruction.",
        "max_retries": 3
    },
    "too_many_tasks": {
        "action": "reduce_tasks",
        "feedback": "Too many tasks. Maximum 3 tasks per request. Combine related changes into fewer tasks.",
        "max_retries": 2
    },
    "missing_content": {
        "action": "add_content",
        "feedback": "Task is missing file content. Include complete file content in the 'content' field.",
        "max_retries": 2
    },
    "missing_filename": {
        "action": "add_filename",
        "feedback": "Task is missing filename. Include 'file_path' field with full path.",
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
    
    # Needs split if score >= 8 (raised from 4 — chat messages naturally contain connectors like "and", "then")
    needs_split = score >= 8
    
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
# CONSOLE ERROR CLASSIFICATION
# ============================================================

CONSOLE_ERROR_PATTERNS = [
    # JavaScript errors
    (r"SyntaxError", "syntax_error"),
    (r"ReferenceError", "reference_error"),
    (r"TypeError", "type_error"),
    (r"RangeError", "runtime_error"),
    (r"URIError", "runtime_error"),
    (r"EvalError", "runtime_error"),
    (r"Uncaught.*Error", "runtime_error"),
    # React/JSX errors
    (r"Invalid hook call", "render_error"),
    (r"Cannot read propert", "type_error"),
    (r"is not a function", "type_error"),
    (r"is not defined", "reference_error"),
    (r"Unexpected token", "syntax_error"),
    (r"Missing.*in.*expression", "syntax_error"),
    # HTML/CSS errors
    (r"Failed to load resource", "network_error"),
    (r"CORS", "network_error"),
    (r"404|Not Found", "network_error"),
    (r"500|Internal Server Error", "network_error"),
    # Python errors
    (r"IndentationError", "syntax_error"),
    (r"NameError", "reference_error"),
    (r"AttributeError", "type_error"),
    (r"ImportError", "reference_error"),
    (r"ModuleNotFoundError", "reference_error"),
    (r"ValueError", "runtime_error"),
    (r"KeyError", "runtime_error"),
    (r"IndexError", "runtime_error"),
    (r"ZeroDivisionError", "runtime_error"),
    (r"FileNotFoundError", "file_not_found"),
    (r"PermissionError", "runtime_error"),
    (r"Traceback \(most recent call last\)", "runtime_error"),
]


def classify_console_error(error_message: str) -> Tuple[str, str]:
    """
    Classify a console error message into an error type.
    
    Args:
        error_message: The raw error message from console
    
    Returns:
        (error_type, cleaned_message)
    """
    for pattern, error_type in CONSOLE_ERROR_PATTERNS:
        if re.search(pattern, error_message, re.IGNORECASE):
            return error_type, error_message
    
    # Default to generic console error
    return "console_error", error_message


def build_error_feedback(error_type: str, error_message: str, code_context: str = "") -> str:
    """
    Build detailed feedback for LLM retry based on console error.
    
    Args:
        error_type: Classified error type
        error_message: Original error message
        code_context: Optional code snippet that caused the error
    
    Returns:
        Feedback string for retry prompt
    """
    base_feedback = NEGOTIATION_STRATEGIES.get(error_type, {}).get("feedback", "Fix the error.")
    
    feedback_parts = [
        f"ERROR TYPE: {error_type}",
        f"ERROR MESSAGE: {error_message}",
        f"REQUIRED ACTION: {base_feedback}"
    ]
    
    if code_context:
        feedback_parts.append(f"CODE CONTEXT:\n```\n{code_context[:500]}\n```")
    
    # Add specific hints based on error type
    hints = {
        "syntax_error": "Check for missing brackets, quotes, semicolons, or indentation.",
        "reference_error": "Ensure all variables and functions are defined before use.",
        "type_error": "Check that you're calling methods on correct types (not null/undefined).",
        "render_error": "Verify React component structure, JSX syntax, and hook usage.",
        "network_error": "Use proper error handling for fetch/API calls."
    }
    
    if error_type in hints:
        feedback_parts.append(f"HINT: {hints[error_type]}")
    
    return "\n".join(feedback_parts)


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
    
    # Log instruction complexity (informational only — never block chat messages)
    complexity = analyze_instruction_complexity(instruction)
    print(f"   Complexity score: {complexity['complexity_score']}")
    
    # Get active skills context
    skill_context = ""
    try:
        from ..skills import build_skill_context, get_active_skills
        active = get_active_skills()
        if active:
            skill_context = build_skill_context()
            print(f"   🎯 Active skills: {[s.name for s in active]}")
    except Exception:
        pass  # Skills not available
    
    # Build system prompt FROM CONSTRAINTS + LEARNED ERRORS
    system_prompt = build_system_prompt(project)
    
    # Get additional learned errors context
    error_context = get_error_context_for_retry(project)
    full_context = f"SYSTEM:\n{system_prompt}\n\n{context}"
    
    # Add skill context if available
    if skill_context:
        full_context += f"\n\n{skill_context}"
    
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
            attempt["raw_response"] = response
            attempts.append(attempt)
            
            learn_from_error(project, error_type, validation.get("detail", ""), 
                           {"instruction": instruction[:200]})
            
            if not should_retry(error_type, retry_count):
                print(f"      Max retries for {error_type} reached")
                break
            retry_count += 1
            continue
        
        # Validate tasks match instruction (prevent creating unrelated files)
        task_match = validate_tasks_match_instruction(validation["tasks"], instruction)
        if not task_match["valid"]:
            error_type = task_match.get("error_type", "task_mismatch")
            print(f"      ❌ Task mismatch: {task_match.get('detail', '')[:100]}")
            attempt["error_type"] = error_type
            attempt["error"] = task_match.get("detail", "")
            attempts.append(attempt)
            
            learn_from_error(project, error_type, task_match.get("detail", ""),
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
            "message": validation.get("message", ""),
            "raw_response": response,
            "attempts": attempts,
            "usage": result.get("usage", {})
        }
    
    # All retries failed — include last raw response for fallback
    last_raw = ""
    if attempts:
        # Find the last attempt that had a response
        for a in reversed(attempts):
            if a.get("raw_response"):
                last_raw = a["raw_response"]
                break
    return False, {
        "error": attempts[-1].get("error_type", "unknown") if attempts else "no_attempts",
        "detail": attempts[-1].get("error", "") if attempts else "",
        "raw_response": last_raw,
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
    
    # Check for tasks and message
    tasks = data.get("tasks", [])
    message = data.get("message", "")
    
    # If there's a message but no tasks, it's a valid conversation response
    if message and not tasks:
        return {"valid": True, "tasks": [], "message": message}
    
    # If no tasks and no message, it's invalid
    if not tasks and not message:
        return {
            "valid": False,
            "error_type": "no_tasks",
            "detail": "Response contains no tasks and no message"
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
            if not content or len(content) < 10:
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
    
    return {"valid": True, "tasks": tasks, "message": message}


def validate_tasks_match_instruction(tasks: List[Dict], instruction: str, target_file: str = None) -> Dict:
    """
    Validate that generated tasks actually match the instruction.
    
    Prevents Claude from generating unrelated files instead of 
    modifying the requested files.
    
    Args:
        tasks: List of tasks from Claude
        instruction: The instruction given
        target_file: Specific file that must be modified (if known)
    
    Returns:
        {"valid": bool, "error_type": str, "detail": str}
    """
    instruction_lower = instruction.lower()
    
    # Extract file paths mentioned in instruction
    import re
    mentioned_files = re.findall(r'[\w/\-_.]+\.(?:py|js|ts|html|css|json|md)', instruction)
    
    # Use explicit target_file if provided
    if target_file:
        mentioned_files = [target_file]
    
    # Check if instruction mentions specific files to modify
    modify_keywords = ['modify', 'update', 'fix', 'edit', 'change', 'patch', 'correct', 'in ']
    is_modify_instruction = any(kw in instruction_lower for kw in modify_keywords) and mentioned_files
    
    if not is_modify_instruction:
        # Instruction doesn't specify files to modify, allow any tasks
        return {"valid": True}
    
    # For modify instructions, at least one task must modify the target file
    target = mentioned_files[0] if mentioned_files else None
    if not target:
        return {"valid": True}
    
    target_basename = target.split('/')[-1]
    
    # Check if ANY task modifies the target file
    task_modifies_target = False
    wrong_files = []
    
    for task in tasks:
        file_path = task.get("file_path") or task.get("filename") or task.get("file") or task.get("path") or ""
        
        # Check if this task targets the correct file
        if file_path == target or file_path.endswith(target_basename):
            task_modifies_target = True
            break
        else:
            wrong_files.append(file_path)
    
    if not task_modifies_target:
        return {
            "valid": False,
            "error_type": "task_mismatch",
            "detail": f"CONSTRAINT VIOLATION: Instruction requires modifying '{target}' but tasks create: {wrong_files}. You MUST return a task with file_path='{target}' containing the modified file content. DO NOT create new files in Txxx/ folders."
        }
    
    return {"valid": True}
