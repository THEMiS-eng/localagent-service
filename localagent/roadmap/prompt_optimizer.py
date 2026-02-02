"""
LocalAgent - ROADMAP: Prompt Optimizer (ADVANCED LINTER)
🔍 Analyse et optimise les prompts AVANT envoi à Claude

FEATURES:
1. Language detection (FR/EN)
2. Task type inference (create/modify/explain/fix)
3. Specificity scoring
4. Conflict resolution
5. Auto-fix with smart rewrites
6. Token estimation
7. Success prediction based on patterns
8. Context awareness
"""

import re
from typing import Dict, List, Tuple


# ============================================================
# LANGUAGE DETECTION
# ============================================================

FR_INDICATORS = [
    # Common French words
    r"\b(le|la|les|un|une|des|du|de|au|aux)\b",
    r"\b(je|tu|il|elle|nous|vous|ils|elles|on)\b",
    r"\b(mon|ma|mes|ton|ta|tes|son|sa|ses|notre|votre|leur)\b",
    r"\b(ce|cette|ces|cet)\b",
    r"\b(qui|que|quoi|quel|quelle|quels|quelles|dont|où)\b",
    r"\b(est|sont|suis|es|sommes|êtes|était|serait|sera|fera)\b",
    r"\b(avoir|être|faire|aller|pouvoir|vouloir|devoir)\b",
    r"\b(dans|sur|sous|avec|pour|sans|par|chez|vers)\b",
    r"\b(mais|ou|et|donc|or|ni|car|puis|ensuite)\b",
    r"\b(très|plus|moins|bien|mal|peu|beaucoup|trop)\b",
    r"\b(oui|non|peut-être|merci|bonjour|salut|bonsoir)\b",
    r"\b(comment|pourquoi|quand|combien|demain|aujourd'hui|hier)\b",
    r"\b(temps|jour|nuit|matin|soir|semaine|mois|année)\b",
    # Action verbs for code
    r"\b(créer|crée|créez|génère|générer|écris|écrire|modifier|ajouter|supprimer)\b",
    r"\b(fichier|page|jeu|projet|application|fonction)\b",
    r"\b(s'il vous plaît|svp)\b",
    # French contractions and special chars (but not English contractions like n't)
    r"(?<![a-z])(qu'|l'|d'|s'|j'|c'|m'|t')",  # French contractions at word boundaries
    r"[àâäéèêëïîôùûüç]",
]

EN_INDICATORS = [
    # Common English words
    r"\b(the|a|an|this|that|these|those)\b",
    r"\b(i|you|he|she|it|we|they)\b",
    r"\b(my|your|his|her|its|our|their)\b",
    r"\b(is|are|am|was|were|been|being|will|would|could|should)\b",
    r"\b(have|has|had|do|does|did|can|may|might|must)\b",
    r"\b(in|on|at|to|from|with|for|by|about|into)\b",
    r"\b(and|or|but|so|if|then|because|when|while)\b",
    r"\b(very|more|less|well|much|many|too|also)\b",
    r"\b(yes|no|maybe|thanks|thank|hello|hi|hey)\b",
    r"\b(what|who|where|when|why|how|which)\b",
    r"\b(time|day|night|morning|evening|week|month|year)\b",
    r"\b(weather|tomorrow|today|yesterday)\b",
    # Action verbs for code
    r"\b(create|generate|write|modify|add|delete|remove|build|make)\b",
    r"\b(file|page|game|project|application|function|component)\b",
    r"\b(please)\b",
]

def detect_language(text: str) -> str:
    """Detect FR or EN based on keyword frequency."""
    text_lower = text.lower()
    
    fr_score = sum(1 for p in FR_INDICATORS if re.search(p, text_lower))
    en_score = sum(1 for p in EN_INDICATORS if re.search(p, text_lower))
    
    # Debug: uncomment to see scores
    # print(f"Language detection: FR={fr_score} EN={en_score} -> {'fr' if fr_score > en_score else 'en'}")
    
    return "fr" if fr_score > en_score else "en"


# ============================================================
# TASK TYPE INFERENCE
# ============================================================

# Patterns that indicate this is NOT a task but just conversation
CONVERSATION_PATTERNS = [
    r"^(hi|hello|hey|bonjour|salut|coucou)\b",
    r"^(thanks|thank you|merci)\b",
    r"^(ok|okay|d'accord|compris)\b",
    r"^(yes|no|oui|non)\b",
    r"\b(this is a test|ceci est un test)\b",
    r"\b(just (a )?test|juste un test)\b",
    r"^what('s| is) (up|new)\b",
    r"^how are you\b",
    r"^(comment (ça va|vas-tu)|ça va)\b",
    r"\b(conversation|chat|discuss|talk|parler|discuter)\b(?!.*(create|make|build|file|code))",
    r"^[^a-zA-Z]*$",  # Only punctuation/emoji
]

TASK_PATTERNS = {
    "create": {
        "en": [r"\b(create|generate|write|build|make|new)\s+\w+", r"\b(create|generate|write|build|make)\b.*\b(file|page|component|function|code|script|game)\b"],
        "fr": [r"\b(cr[ée]er|cr[ée]e|g[ée]n[èe]re|g[ée]n[ée]rer|[ée]cris|[ée]crire|construire|nouveau|fabriquer|d[ée]velopper|coder)\s+\w+", r"\b(cr[ée]er|faire)\b.*\b(fichier|page|jeu|application|script|code)\b"],
        "output": "file"
    },
    "modify": {
        "en": [r"\b(modify|change|update|edit|fix|refactor|improve)\s+\w+", r"\b(modify|change|update|edit)\b.*\b(file|code|function)\b"],
        "fr": [r"\b(modifier|changer|mettre [àa] jour|[ée]diter|corriger|am[ée]liorer)\s+\w+"],
        "output": "diff"
    },
    "explain": {
        "en": [r"\b(explain|describe|what is|how does|tell me about)\s+\w+"],
        "fr": [r"\b(explique|expliquer|d[ée]cris|d[ée]crire|c'est quoi|comment)\s+\w+"],
        "output": "text"
    },
    "analyze": {
        "en": [r"\b(analyze|review|check|audit|evaluate)\s+\w+"],
        "fr": [r"\b(analyser|analyse|v[ée]rifier|[ée]valuer|examiner)\s+\w+"],
        "output": "report"
    },
    "fix": {
        "en": [r"\b(fix|debug|solve|resolve|repair)\s+\w+", r"\b(fix|debug)\b.*\b(bug|error|issue|problem)\b"],
        "fr": [r"\b(corriger|r[ée]parer|r[ée]soudre|debugger|fixer)\s+\w+"],
        "output": "code"
    }
}


def is_conversational(text: str) -> bool:
    """
    Detect if the message is just conversation, not a task request.
    
    Returns True if this is casual conversation that shouldn't trigger task execution.
    """
    text_lower = text.lower().strip()
    
    # Very short messages are usually conversation
    if len(text_lower) < 10:
        return True
    
    # First check if there are action verbs - if yes, it's probably a task
    # English action verbs
    en_verbs = r"\b(create|make|build|write|generate|modify|change|update|fix|add|remove|delete|explain|analyze|review)\b"
    # French action verbs - conjugations that imply a command/request
    # "crée", "créer", "fais-moi", "génère", "écris"... but NOT "fait-il" (question)
    fr_task_patterns = [
        r"\b(cr[ée]+[ersz]?)\s+\w+",  # crée/créer/créez followed by something
        r"\b(fais|faites)[\s-]+(moi|nous|un|une|le|la)",  # fais-moi, fais un...
        r"\b(construi[rstz]+)\s+\w+",  # construis/construire
        r"\b([ée]cri[rstz]+)\s+\w+",  # écris/écrire  
        r"\b(g[ée]n[èeé]r[eé]?[rsz]?)\s+\w+",  # génère/générer
        r"\b(modifi[eé]?[rsz]?)\s+\w+",  # modifie/modifier
        r"\b(ajout[eé]?[rsz]?)\s+\w+",  # ajoute/ajouter
        r"\b(supprim[eé]?[rsz]?)\s+\w+",  # supprime/supprimer
        r"\b(corrig[eé]?[rsz]?)\s+\w+",  # corrige/corriger
        r"\b(d[ée]velopp[eé]?[rsz]?)\s+\w+",  # développe/développer
        r"\b(cod[eé]?[rsz]?)\s+\w+",  # code/coder
        r"\b(programm[eé]?[rsz]?)\s+\w+",  # programme/programmer
        r"\b(fabriqu[eé]?[rsz]?)\s+\w+",  # fabrique/fabriquer
    ]
    
    # If we find English action verbs, it's NOT conversation
    if re.search(en_verbs, text_lower):
        return False
    
    # Check French task patterns
    for pattern in fr_task_patterns:
        if re.search(pattern, text_lower):
            return False
    
    # Check conversation patterns
    for pattern in CONVERSATION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    
    # No action verbs found = probably conversation
    return True


def infer_task_type(text: str, lang: str = "en") -> Dict:
    """Infer what type of task the user wants."""
    text_lower = text.lower()
    
    # First check if this is just conversation
    if is_conversational(text):
        return {"type": "conversation", "expected_output": "response", "confidence": 0.9}
    
    for task_type, config in TASK_PATTERNS.items():
        patterns = config.get(lang, config.get("en", []))
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return {
                    "type": task_type,
                    "expected_output": config["output"],
                    "confidence": 0.8
                }
    
    return {"type": "unknown", "expected_output": "unknown", "confidence": 0.3}


# ============================================================
# SPECIFICITY SCORING
# ============================================================

def calculate_specificity(text: str, lang: str = "en") -> Dict:
    """
    Calculate how specific/detailed the prompt is.
    Returns score 0-100 and suggestions.
    """
    score = 50  # Base score
    suggestions = []
    
    # Length bonus (longer usually more specific)
    word_count = len(text.split())
    if word_count > 20:
        score += 15
    elif word_count > 10:
        score += 8
    elif word_count < 5:
        score -= 20
        suggestions.append("Add more details to your request")
    
    # Technical terms bonus
    tech_terms = [
        r"\b(html|css|javascript|python|react|vue|api|json|database|server)\b",
        r"\b(function|class|method|variable|array|object|loop)\b",
        r"\b(responsive|mobile|desktop|animation|style)\b"
    ]
    tech_count = sum(1 for p in tech_terms if re.search(p, text.lower()))
    score += min(tech_count * 5, 20)
    
    # Numbers/quantities bonus (shows specificity)
    if re.search(r"\b\d+\b", text):
        score += 10
    else:
        suggestions.append("Add specific numbers (e.g., '5 items', '100px')")
    
    # File extension mentioned
    if re.search(r"\.\w{2,4}\b", text):
        score += 10
    
    # Color/size/dimension mentioned
    if re.search(r"(#[0-9a-f]{3,6}|\b\d+px\b|\brgb|\brem\b)", text.lower()):
        score += 5
    
    # Vague words penalty
    vague_words = [r"\b(something|stuff|thing|some|maybe|probably|etc)\b"]
    vague_count = sum(len(re.findall(p, text.lower())) for p in vague_words)
    score -= vague_count * 8
    if vague_count > 0:
        suggestions.append("Replace vague words with specific terms")
    
    return {
        "score": max(0, min(100, score)),
        "word_count": word_count,
        "suggestions": suggestions
    }


# ============================================================
# TOKEN ESTIMATION
# ============================================================

def estimate_tokens(text: str) -> Dict:
    """Estimate token count and cost."""
    # Rough estimation: ~4 chars per token for English, ~3 for code-heavy
    char_count = len(text)
    has_code = bool(re.search(r"```|function|class|def |import ", text))
    
    chars_per_token = 3 if has_code else 4
    input_tokens = char_count // chars_per_token
    
    # Estimate output based on task type
    task = infer_task_type(text)
    output_multipliers = {
        "create": 15,  # Creates lots of code
        "modify": 5,
        "explain": 8,
        "analyze": 10,
        "fix": 6,
        "unknown": 8
    }
    estimated_output = input_tokens * output_multipliers.get(task["type"], 8)
    
    # Cost estimation (Claude Sonnet pricing)
    input_cost = (input_tokens / 1000) * 0.003
    output_cost = (estimated_output / 1000) * 0.015
    
    return {
        "input_tokens": input_tokens,
        "estimated_output_tokens": estimated_output,
        "estimated_cost": round(input_cost + output_cost, 4),
        "cost_breakdown": {
            "input": round(input_cost, 5),
            "output": round(output_cost, 5)
        }
    }


# ============================================================
# ISSUE DETECTION PATTERNS (Enhanced)
# ============================================================

LINT_RULES = {
    "negation": {
        "patterns": {
            "en": [r"\bdon'?t\b", r"\bnot\b", r"\bnever\b", r"\bwithout\b", r"\bavoid\b", r"\bno\s+\w+"],
            "fr": [r"\bne\s+pas\b", r"\bpas\s+de\b", r"\bjamais\b", r"\bsans\b", r"\béviter\b"]
        },
        "severity": "high",
        "message": {"en": "Negations detected", "fr": "Négations détectées"},
        "fix": {"en": "Reframe positively", "fr": "Reformuler positivement"}
    },
    "conflict": {
        "patterns": {
            "en": [r"\bbut\s+also\b", r"\bshort\b.*\bdetailed\b", r"\bsimple\b.*\bcomprehensive\b"],
            "fr": [r"\bmais\s+aussi\b", r"\bcourt\b.*\bdétaillé\b", r"\bsimple\b.*\bcomplet\b"]
        },
        "severity": "high",
        "message": {"en": "Conflicting instructions", "fr": "Instructions contradictoires"},
        "fix": {"en": "Choose one direction", "fr": "Choisir une direction"}
    },
    "ambiguous_scope": {
        "patterns": {
            "en": [r"\bsome\b", r"\ba\s+few\b", r"\bvarious\b", r"\betc\.?\b"],
            "fr": [r"\bquelques\b", r"\bplusieurs\b", r"\bdivers\b", r"\betc\.?\b"]
        },
        "severity": "medium",
        "message": {"en": "Ambiguous scope", "fr": "Portée ambiguë"},
        "fix": {"en": "Add specific quantities", "fr": "Ajouter des quantités précises"}
    },
    "vague_reference": {
        "patterns": {
            "en": [r"\bthis\b(?!\s+\w+\s+\w+)", r"\bthat\b(?!\s+\w+)", r"\bit\b(?!\s+\w+)", r"\bthe\s+thing\b"],
            "fr": [r"\bça\b", r"\bceci\b", r"\bcela\b", r"\ble\s+truc\b"]
        },
        "severity": "medium",
        "message": {"en": "Vague references", "fr": "Références vagues"},
        "fix": {"en": "Name explicitly", "fr": "Nommer explicitement"}
    },
    "missing_format": {
        "patterns": {
            "en": [r"^(?!.*(?:json|html|python|file|format)).*(?:create|generate|write)\b"],
            "fr": [r"^(?!.*(?:json|html|python|fichier|format)).*(?:créer|génère|écris)\b"]
        },
        "severity": "medium",
        "message": {"en": "No output format specified", "fr": "Format de sortie non spécifié"},
        "fix": {"en": "Specify format (HTML, JSON, etc.)", "fr": "Spécifier le format (HTML, JSON, etc.)"}
    },
    "too_complex": {
        "patterns": {
            "en": [r"\band\s+then\b", r"\bfirst\b.*\bthen\b.*\bfinally\b", r"\balso\b.*\balso\b"],
            "fr": [r"\bet\s+ensuite\b", r"\bd'abord\b.*\bpuis\b.*\benfin\b", r"\baussi\b.*\baussi\b"]
        },
        "severity": "high",
        "message": {"en": "Multiple steps detected", "fr": "Plusieurs étapes détectées"},
        "fix": {"en": "Split into separate requests", "fr": "Diviser en requêtes séparées"}
    }
}


# ============================================================
# MAIN LINT FUNCTION
# ============================================================

def lint_prompt(prompt: str) -> Dict:
    """
    Comprehensive prompt analysis.
    """
    # Detect language
    lang = detect_language(prompt)
    
    # Infer task type
    task = infer_task_type(prompt, lang)
    
    # Calculate specificity
    specificity = calculate_specificity(prompt, lang)
    
    # Estimate tokens
    tokens = estimate_tokens(prompt)
    
    # Detect issues - check patterns for BOTH languages to catch mixed content
    issues = []
    prompt_lower = prompt.lower()
    
    for rule_name, rule in LINT_RULES.items():
        matches = []
        
        # Check patterns for ALL languages (not just detected one)
        for lang_key in ["en", "fr"]:
            patterns = rule["patterns"].get(lang_key, [])
            for pattern in patterns:
                for match in re.finditer(pattern, prompt_lower, re.IGNORECASE):
                    matches.append(match.group())
        
        if matches:
            issues.append({
                "type": rule_name,
                "severity": rule["severity"],
                "message": rule["message"].get(lang, rule["message"].get("en", "")),
                "matches": list(set(matches))[:3],
                "fix": rule["fix"].get(lang, rule["fix"].get("en", ""))
            })
    
    # Calculate overall score
    severity_weights = {"high": 20, "medium": 10, "low": 5}
    issue_penalty = sum(severity_weights.get(i["severity"], 5) for i in issues)
    
    # Combine with specificity
    base_score = (specificity["score"] + 100) // 2
    final_score = max(0, min(100, base_score - issue_penalty))
    
    # Generate optimized prompt
    optimized = optimize_prompt(prompt, issues, lang)
    
    # Collect all suggestions
    suggestions = specificity["suggestions"] + [i["fix"] for i in issues]
    
    return {
        "language": lang,
        "task_type": task,
        "specificity": specificity,
        "tokens": tokens,
        "issues": issues,
        "issue_count": len(issues),
        "score": final_score,
        "optimized": optimized,
        "suggestions": list(set(suggestions)),
        "needs_optimization": final_score < 70
    }


# ============================================================
# OPTIMIZATION ENGINE
# ============================================================

def optimize_prompt(prompt: str, issues: List[Dict] = None, lang: str = "en") -> str:
    """Apply automatic fixes to improve the prompt."""
    if issues is None:
        result = lint_prompt(prompt)
        issues = result["issues"]
        lang = result["language"]
    
    optimized = prompt
    
    for issue in issues:
        issue_type = issue["type"]
        
        if issue_type == "negation":
            optimized = _reframe_negations(optimized, lang)
        elif issue_type == "conflict":
            optimized = _resolve_conflicts(optimized, lang)
        elif issue_type == "vague_reference":
            optimized = _clarify_references(optimized, lang)
        elif issue_type == "ambiguous_scope":
            optimized = _add_scope_hints(optimized, lang)
        elif issue_type == "missing_format":
            optimized = _add_format_spec(optimized, lang)
    
    # Ensure file content instruction for create tasks
    task = infer_task_type(optimized, lang)
    if task["type"] == "create":
        if lang == "fr":
            if "contenu" not in optimized.lower():
                optimized += "\n\nIMPORTANT: Inclure le contenu complet du fichier."
        else:
            if "content" not in optimized.lower():
                optimized += "\n\nIMPORTANT: Include complete file content."
    
    return optimized.strip()


def _reframe_negations(prompt: str, lang: str = "en") -> str:
    """Reframe negative instructions positively."""
    if lang == "fr":
        replacements = [
            (r"\bne\s+pas\s+utiliser\s+de\s+boucles?\b", "utiliser des list comprehensions"),
            (r"\bpas\s+de\s+commentaires?\b", "code auto-documenté"),
            (r"\bpas\s+trop\s+long\b", "concis (max 100 lignes)"),
            (r"\bpas\s+de\s+bullet\s*points?\b", "utiliser des paragraphes"),
            (r"\bsans\s+dépendances?\b", "avec la bibliothèque standard uniquement"),
            (r"\béviter\b", "minimiser"),
        ]
    else:
        replacements = [
            (r"\bdon'?t\s+use\s+loops?\b", "use list comprehensions"),
            (r"\bdon'?t\s+add\s+comments?\b", "write self-documenting code"),
            (r"\bdon'?t\s+make\s+it\s+long\b", "keep it concise (max 100 lines)"),
            (r"\bdon'?t\s+use\s+bullet\s*points?\b", "use prose paragraphs"),
            (r"\bwithout\s+dependencies\b", "using only standard library"),
            (r"\bavoid\s+errors?\b", "implement error handling"),
            (r"\bno\s+external\b", "use built-in only"),
            (r"\bnot\s+too\s+long\b", "concise"),
            (r"\bnot\s+too\s+short\b", "detailed"),
        ]
    
    result = prompt
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def _resolve_conflicts(prompt: str, lang: str = "en") -> str:
    """Resolve conflicting instructions."""
    if lang == "fr":
        replacements = [
            (r"\b(court|bref)\b(.{0,20})\b(détaillé|complet)\b", r"détaillé (max 200 mots)"),
            (r"\b(simple)\b(.{0,20})\b(complet|exhaustif)\b", r"complet avec structure claire"),
        ]
    else:
        replacements = [
            (r"\b(short|brief)\b(.{0,20})\b(detailed|comprehensive)\b", r"detailed (max 200 words)"),
            (r"\b(detailed|comprehensive)\b(.{0,20})\b(short|brief)\b", r"detailed (max 200 words)"),
            (r"\b(simple)\b(.{0,20})\b(comprehensive)\b", r"comprehensive with clear structure"),
            (r"\b(quick)\b(.{0,20})\b(thorough)\b", r"thorough"),
        ]
    
    result = prompt
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def _clarify_references(prompt: str, lang: str = "en") -> str:
    """Make vague references more specific."""
    if lang == "fr":
        if re.search(r"\bmon\s+projet\b", prompt, re.IGNORECASE):
            prompt = prompt + " (le projet actuel)"
        prompt = re.sub(r"\ble\s+code\b", "les fichiers source", prompt, flags=re.IGNORECASE)
    else:
        if re.search(r"\bmy\s+project\b", prompt, re.IGNORECASE):
            prompt = prompt + " (the current project)"
        prompt = re.sub(r"\bthe\s+code\b", "the source files", prompt, flags=re.IGNORECASE)
    return prompt


def _add_scope_hints(prompt: str, lang: str = "en") -> str:
    """Add scope clarification."""
    if lang == "fr":
        prompt = re.sub(r"\bquelques\b", "3-5", prompt, flags=re.IGNORECASE)
        prompt = re.sub(r"\bplusieurs\b", "4-6", prompt, flags=re.IGNORECASE)
    else:
        prompt = re.sub(r"\bsome\b", "3-5", prompt, flags=re.IGNORECASE)
        prompt = re.sub(r"\ba\s+few\b", "2-3", prompt, flags=re.IGNORECASE)
        prompt = re.sub(r"\bseveral\b", "4-6", prompt, flags=re.IGNORECASE)
    return prompt


def _add_format_spec(prompt: str, lang: str = "en") -> str:
    """Add output format specification."""
    task = infer_task_type(prompt, lang)
    
    if task["type"] == "create":
        if lang == "fr":
            if not re.search(r"\b(html|json|python|fichier)\b", prompt, re.IGNORECASE):
                prompt += " Retourner comme fichier HTML unique avec CSS/JS intégré."
        else:
            if not re.search(r"\b(html|json|python|file)\b", prompt, re.IGNORECASE):
                prompt += " Return as a single HTML file with embedded CSS/JS."
    return prompt


# ============================================================
# INTEGRATION HELPERS
# ============================================================

def preprocess_for_negotiation(prompt: str, project: str = None) -> Tuple[str, Dict]:
    """Preprocess prompt before sending to negotiator."""
    report = lint_prompt(prompt)
    
    if report["issues"]:
        print(f"🔍 Linter [{report['language'].upper()}]: {report['issue_count']} issues (score: {report['score']})", flush=True)
        for issue in report["issues"]:
            print(f"   ⚠️ {issue['message']}: {', '.join(issue['matches'][:2])}", flush=True)
    else:
        print(f"🔍 Linter: OK (score: {report['score']})", flush=True)
    
    print(f"   📊 Task: {report['task_type']['type']} | Specificity: {report['specificity']['score']} | Est. cost: ${report['tokens']['estimated_cost']}", flush=True)
    
    return report["optimized"], report


def get_lint_summary(prompt: str) -> str:
    """Get human-readable lint summary."""
    report = lint_prompt(prompt)
    
    lines = [f"🔍 Prompt Analysis (score: {report['score']}/100)"]
    lines.append(f"   Language: {report['language'].upper()}")
    lines.append(f"   Task type: {report['task_type']['type']}")
    lines.append(f"   Specificity: {report['specificity']['score']}/100")
    lines.append(f"   Est. tokens: ~{report['tokens']['input_tokens']} in / ~{report['tokens']['estimated_output_tokens']} out")
    lines.append(f"   Est. cost: ${report['tokens']['estimated_cost']}")
    
    if report["issues"]:
        lines.append(f"\n   Issues ({len(report['issues'])}):")
        severity_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        for issue in report["issues"]:
            icon = severity_icons.get(issue["severity"], "⚪")
            lines.append(f"   {icon} {issue['message']}")
    
    return "\n".join(lines)
