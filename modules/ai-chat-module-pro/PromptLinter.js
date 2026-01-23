/**
 * PromptLinter.js
 * 
 * JavaScript port of LocalAgent's prompt_optimizer.py
 * Analyzes and optimizes prompts BEFORE sending to Claude
 * 
 * FEATURES:
 * 1. Language detection (FR/EN)
 * 2. Task type inference (create/modify/explain/fix)
 * 3. Specificity scoring
 * 4. Issue detection (negations, conflicts, vague refs)
 * 5. Auto-fix with smart rewrites
 * 6. Token estimation
 * 7. Success prediction
 */

// ============================================================
// LANGUAGE DETECTION
// ============================================================

const FR_INDICATORS = [
  /\b(créer|crée|créez|génère|générer|écris|écrire|modifier|ajouter|supprimer)\b/i,
  /\b(avec|pour|dans|sur|une?|les?|des?|mon|ma|mes|ce|cette)\b/i,
  /\b(fichier|page|jeu|projet|application|fonction)\b/i,
  /\b(s'il vous plaît|svp|merci)\b/i,
];

const EN_INDICATORS = [
  /\b(create|generate|write|modify|add|delete|remove|build|make)\b/i,
  /\b(with|for|the|a|an|my|this|that)\b/i,
  /\b(file|page|game|project|application|function|component)\b/i,
  /\b(please|thanks)\b/i,
];

export function detectLanguage(text) {
  const textLower = text.toLowerCase();
  
  const frScore = FR_INDICATORS.filter(p => p.test(textLower)).length;
  const enScore = EN_INDICATORS.filter(p => p.test(textLower)).length;
  
  return frScore > enScore ? 'fr' : 'en';
}

// ============================================================
// TASK TYPE INFERENCE
// ============================================================

const TASK_PATTERNS = {
  create: {
    en: [/\b(create|generate|write|build|make|new)\b/i],
    fr: [/\b(créer|crée|génère|générer|écris|écrire|construire|nouveau)\b/i],
    output: 'file'
  },
  modify: {
    en: [/\b(modify|change|update|edit|fix|refactor|improve)\b/i],
    fr: [/\b(modifier|changer|mettre à jour|éditer|corriger|améliorer)\b/i],
    output: 'diff'
  },
  explain: {
    en: [/\b(explain|describe|what is|how does|tell me about)\b/i],
    fr: [/\b(explique|expliquer|décris|décrire|c'est quoi|comment)\b/i],
    output: 'text'
  },
  analyze: {
    en: [/\b(analyze|review|check|audit|evaluate)\b/i],
    fr: [/\b(analyser|analyse|vérifier|évaluer|examiner)\b/i],
    output: 'report'
  },
  fix: {
    en: [/\b(fix|debug|solve|resolve|repair)\b/i],
    fr: [/\b(corriger|réparer|résoudre|debugger|fixer)\b/i],
    output: 'code'
  }
};

export function inferTaskType(text, lang = 'en') {
  const textLower = text.toLowerCase();
  
  for (const [taskType, config] of Object.entries(TASK_PATTERNS)) {
    const patterns = config[lang] || config.en || [];
    for (const pattern of patterns) {
      if (pattern.test(textLower)) {
        return {
          type: taskType,
          expectedOutput: config.output,
          confidence: 0.8
        };
      }
    }
  }
  
  return { type: 'unknown', expectedOutput: 'unknown', confidence: 0.3 };
}

// ============================================================
// SPECIFICITY SCORING
// ============================================================

export function calculateSpecificity(text, lang = 'en') {
  let score = 50;
  const suggestions = [];
  
  const wordCount = text.split(/\s+/).length;
  
  if (wordCount > 20) {
    score += 15;
  } else if (wordCount > 10) {
    score += 8;
  } else if (wordCount < 5) {
    score -= 20;
    suggestions.push(lang === 'fr' 
      ? 'Ajoutez plus de détails à votre demande'
      : 'Add more details to your request');
  }
  
  // Technical terms bonus
  const techTerms = [
    /\b(html|css|javascript|python|react|vue|api|json|database|server)\b/i,
    /\b(function|class|method|variable|array|object|loop)\b/i,
    /\b(responsive|mobile|desktop|animation|style)\b/i
  ];
  const techCount = techTerms.filter(p => p.test(text)).length;
  score += Math.min(techCount * 5, 20);
  
  // Numbers bonus
  if (/\b\d+\b/.test(text)) {
    score += 10;
  } else {
    suggestions.push(lang === 'fr'
      ? 'Ajoutez des nombres spécifiques (ex: "5 éléments", "100px")'
      : 'Add specific numbers (e.g., "5 items", "100px")');
  }
  
  // File extension bonus
  if (/\.\w{2,4}\b/.test(text)) {
    score += 10;
  }
  
  // Color/size/dimension bonus
  if (/(#[0-9a-f]{3,6}|\b\d+px\b|\brgb|\brem\b)/i.test(text)) {
    score += 5;
  }
  
  // Vague words penalty
  const vagueWords = /\b(something|stuff|thing|some|maybe|probably|etc)\b/gi;
  const vagueCount = (text.match(vagueWords) || []).length;
  score -= vagueCount * 8;
  if (vagueCount > 0) {
    suggestions.push(lang === 'fr'
      ? 'Remplacez les mots vagues par des termes précis'
      : 'Replace vague words with specific terms');
  }
  
  return {
    score: Math.max(0, Math.min(100, score)),
    wordCount,
    suggestions
  };
}

// ============================================================
// TOKEN ESTIMATION
// ============================================================

export function estimateTokens(text) {
  const charCount = text.length;
  const hasCode = /```|function|class|def |import /.test(text);
  
  const charsPerToken = hasCode ? 3 : 4;
  const inputTokens = Math.ceil(charCount / charsPerToken);
  
  const task = inferTaskType(text);
  const outputMultipliers = {
    create: 15,
    modify: 5,
    explain: 8,
    analyze: 10,
    fix: 6,
    unknown: 8
  };
  const estimatedOutput = inputTokens * (outputMultipliers[task.type] || 8);
  
  // Cost estimation (Claude Sonnet pricing)
  const inputCost = (inputTokens / 1000) * 0.003;
  const outputCost = (estimatedOutput / 1000) * 0.015;
  
  return {
    inputTokens,
    estimatedOutputTokens: estimatedOutput,
    estimatedCost: Math.round((inputCost + outputCost) * 10000) / 10000,
    costBreakdown: {
      input: Math.round(inputCost * 100000) / 100000,
      output: Math.round(outputCost * 100000) / 100000
    }
  };
}

// ============================================================
// LINT RULES
// ============================================================

const LINT_RULES = {
  negation: {
    patterns: {
      en: [/\bdon'?t\b/i, /\bnot\b/i, /\bnever\b/i, /\bwithout\b/i, /\bavoid\b/i, /\bno\s+\w+/i],
      fr: [/\bne\s+pas\b/i, /\bpas\s+de\b/i, /\bjamais\b/i, /\bsans\b/i, /\béviter\b/i]
    },
    severity: 'high',
    message: { en: 'Negations detected', fr: 'Négations détectées' },
    fix: { en: 'Reframe positively', fr: 'Reformuler positivement' }
  },
  conflict: {
    patterns: {
      en: [/\bbut\s+also\b/i, /\bshort\b.*\bdetailed\b/i, /\bsimple\b.*\bcomprehensive\b/i],
      fr: [/\bmais\s+aussi\b/i, /\bcourt\b.*\bdétaillé\b/i, /\bsimple\b.*\bcomplet\b/i]
    },
    severity: 'high',
    message: { en: 'Conflicting instructions', fr: 'Instructions contradictoires' },
    fix: { en: 'Choose one approach', fr: 'Choisir une approche' }
  },
  vagueReference: {
    patterns: {
      en: [/\bthe\s+code\b/i, /\bmy\s+project\b/i, /\bthis\s+thing\b/i],
      fr: [/\ble\s+code\b/i, /\bmon\s+projet\b/i, /\bcette\s+chose\b/i]
    },
    severity: 'medium',
    message: { en: 'Vague references found', fr: 'Références vagues trouvées' },
    fix: { en: 'Be more specific', fr: 'Être plus spécifique' }
  },
  ambiguousScope: {
    patterns: {
      en: [/\bsome\b/i, /\ba\s+few\b/i, /\bseveral\b/i, /\bmany\b/i],
      fr: [/\bquelques\b/i, /\bplusieurs\b/i, /\bbeaucoup\b/i]
    },
    severity: 'low',
    message: { en: 'Ambiguous quantities', fr: 'Quantités ambiguës' },
    fix: { en: 'Use specific numbers', fr: 'Utiliser des nombres précis' }
  },
  missingFormat: {
    patterns: {
      en: [/^(?!.*(html|json|python|markdown|file|format)).*\b(create|generate|write)\b/i],
      fr: [/^(?!.*(html|json|python|markdown|fichier|format)).*\b(créer|générer|écrire)\b/i]
    },
    severity: 'medium',
    message: { en: 'Output format not specified', fr: 'Format de sortie non spécifié' },
    fix: { en: 'Specify desired format', fr: 'Spécifier le format souhaité' }
  }
};

// ============================================================
// MAIN LINTER FUNCTION
// ============================================================

export function lintPrompt(prompt) {
  const lang = detectLanguage(prompt);
  const task = inferTaskType(prompt, lang);
  const specificity = calculateSpecificity(prompt, lang);
  const tokens = estimateTokens(prompt);
  
  const issues = [];
  const promptLower = prompt.toLowerCase();
  
  for (const [ruleName, rule] of Object.entries(LINT_RULES)) {
    const patterns = rule.patterns[lang] || rule.patterns.en || [];
    const matches = [];
    
    for (const pattern of patterns) {
      const found = promptLower.match(pattern);
      if (found) {
        matches.push(...found);
      }
    }
    
    if (matches.length > 0) {
      issues.push({
        type: ruleName,
        severity: rule.severity,
        message: rule.message[lang] || rule.message.en,
        matches: [...new Set(matches)].slice(0, 3),
        fix: rule.fix[lang] || rule.fix.en
      });
    }
  }
  
  // Calculate overall score
  const severityWeights = { high: 20, medium: 10, low: 5 };
  const issuePenalty = issues.reduce((sum, i) => sum + (severityWeights[i.severity] || 5), 0);
  
  const baseScore = Math.floor((specificity.score + 100) / 2);
  const finalScore = Math.max(0, Math.min(100, baseScore - issuePenalty));
  
  // Generate optimized prompt
  const optimized = optimizePrompt(prompt, issues, lang);
  
  // Collect suggestions
  const suggestions = [
    ...specificity.suggestions,
    ...issues.map(i => i.fix)
  ];
  
  return {
    language: lang,
    taskType: task,
    specificity,
    tokens,
    issues,
    issueCount: issues.length,
    score: finalScore,
    optimized,
    suggestions: [...new Set(suggestions)],
    needsOptimization: finalScore < 70
  };
}

// ============================================================
// OPTIMIZATION ENGINE
// ============================================================

export function optimizePrompt(prompt, issues = null, lang = null) {
  if (!issues) {
    const result = lintPrompt(prompt);
    issues = result.issues;
    lang = result.language;
  }
  
  let optimized = prompt;
  
  for (const issue of issues) {
    switch (issue.type) {
      case 'negation':
        optimized = reframeNegations(optimized, lang);
        break;
      case 'conflict':
        optimized = resolveConflicts(optimized, lang);
        break;
      case 'vagueReference':
        optimized = clarifyReferences(optimized, lang);
        break;
      case 'ambiguousScope':
        optimized = addScopeHints(optimized, lang);
        break;
      case 'missingFormat':
        optimized = addFormatSpec(optimized, lang);
        break;
    }
  }
  
  // Ensure file content instruction for create tasks
  const task = inferTaskType(optimized, lang);
  if (task.type === 'create') {
    if (lang === 'fr') {
      if (!/contenu/i.test(optimized)) {
        optimized += '\n\nIMPORTANT: Inclure le contenu complet du fichier.';
      }
    } else {
      if (!/content/i.test(optimized)) {
        optimized += '\n\nIMPORTANT: Include complete file content.';
      }
    }
  }
  
  return optimized.trim();
}

function reframeNegations(prompt, lang = 'en') {
  const replacements = lang === 'fr' ? [
    [/\bne\s+pas\s+utiliser\s+de\s+boucles?\b/gi, 'utiliser des list comprehensions'],
    [/\bpas\s+de\s+commentaires?\b/gi, 'code auto-documenté'],
    [/\bpas\s+trop\s+long\b/gi, 'concis (max 100 lignes)'],
    [/\bsans\s+dépendances?\b/gi, 'avec la bibliothèque standard uniquement'],
    [/\béviter\b/gi, 'minimiser'],
  ] : [
    [/\bdon'?t\s+use\s+loops?\b/gi, 'use list comprehensions'],
    [/\bdon'?t\s+add\s+comments?\b/gi, 'write self-documenting code'],
    [/\bdon'?t\s+make\s+it\s+long\b/gi, 'keep it concise (max 100 lines)'],
    [/\bwithout\s+dependencies\b/gi, 'using only standard library'],
    [/\bavoid\s+errors?\b/gi, 'implement error handling'],
    [/\bno\s+external\b/gi, 'use built-in only'],
    [/\bnot\s+too\s+long\b/gi, 'concise'],
    [/\bnot\s+too\s+short\b/gi, 'detailed'],
  ];
  
  let result = prompt;
  for (const [pattern, replacement] of replacements) {
    result = result.replace(pattern, replacement);
  }
  return result;
}

function resolveConflicts(prompt, lang = 'en') {
  const replacements = lang === 'fr' ? [
    [/\b(court|bref)\b(.{0,20})\b(détaillé|complet)\b/gi, 'détaillé (max 200 mots)'],
    [/\b(simple)\b(.{0,20})\b(complet|exhaustif)\b/gi, 'complet avec structure claire'],
  ] : [
    [/\b(short|brief)\b(.{0,20})\b(detailed|comprehensive)\b/gi, 'detailed (max 200 words)'],
    [/\b(detailed|comprehensive)\b(.{0,20})\b(short|brief)\b/gi, 'detailed (max 200 words)'],
    [/\b(simple)\b(.{0,20})\b(comprehensive)\b/gi, 'comprehensive with clear structure'],
    [/\b(quick)\b(.{0,20})\b(thorough)\b/gi, 'thorough'],
  ];
  
  let result = prompt;
  for (const [pattern, replacement] of replacements) {
    result = result.replace(pattern, replacement);
  }
  return result;
}

function clarifyReferences(prompt, lang = 'en') {
  let result = prompt;
  
  if (lang === 'fr') {
    if (/\bmon\s+projet\b/i.test(result)) {
      result += ' (le projet actuel)';
    }
    result = result.replace(/\ble\s+code\b/gi, 'les fichiers source');
  } else {
    if (/\bmy\s+project\b/i.test(result)) {
      result += ' (the current project)';
    }
    result = result.replace(/\bthe\s+code\b/gi, 'the source files');
  }
  
  return result;
}

function addScopeHints(prompt, lang = 'en') {
  let result = prompt;
  
  if (lang === 'fr') {
    result = result.replace(/\bquelques\b/gi, '3-5');
    result = result.replace(/\bplusieurs\b/gi, '4-6');
  } else {
    result = result.replace(/\bsome\b/gi, '3-5');
    result = result.replace(/\ba\s+few\b/gi, '2-3');
    result = result.replace(/\bseveral\b/gi, '4-6');
  }
  
  return result;
}

function addFormatSpec(prompt, lang = 'en') {
  const task = inferTaskType(prompt, lang);
  
  if (task.type === 'create') {
    if (lang === 'fr') {
      if (!/\b(html|json|python|fichier)\b/i.test(prompt)) {
        prompt += ' Retourner comme fichier HTML unique avec CSS/JS intégré.';
      }
    } else {
      if (!/\b(html|json|python|file)\b/i.test(prompt)) {
        prompt += ' Return as a single HTML file with embedded CSS/JS.';
      }
    }
  }
  
  return prompt;
}

// ============================================================
// INTEGRATION HELPERS
// ============================================================

export function getLintSummary(prompt) {
  const report = lintPrompt(prompt);
  
  const severityIcons = { high: '🔴', medium: '🟡', low: '🟢' };
  
  let summary = `🔍 Prompt Analysis (score: ${report.score}/100)\n`;
  summary += `   Language: ${report.language.toUpperCase()}\n`;
  summary += `   Task type: ${report.taskType.type}\n`;
  summary += `   Specificity: ${report.specificity.score}/100\n`;
  summary += `   Est. tokens: ~${report.tokens.inputTokens} in / ~${report.tokens.estimatedOutputTokens} out\n`;
  summary += `   Est. cost: $${report.tokens.estimatedCost}\n`;
  
  if (report.issues.length > 0) {
    summary += `\n   Issues (${report.issues.length}):\n`;
    for (const issue of report.issues) {
      const icon = severityIcons[issue.severity] || '⚪';
      summary += `   ${icon} ${issue.message}\n`;
    }
  }
  
  return summary;
}

/**
 * React hook for prompt linting
 */
export function useLinter(initialPrompt = '') {
  const [prompt, setPrompt] = useState(initialPrompt);
  const [report, setReport] = useState(null);
  
  useEffect(() => {
    if (prompt.trim()) {
      setReport(lintPrompt(prompt));
    } else {
      setReport(null);
    }
  }, [prompt]);
  
  return {
    prompt,
    setPrompt,
    report,
    optimized: report?.optimized || prompt,
    score: report?.score || 100,
    issues: report?.issues || [],
    suggestions: report?.suggestions || [],
    needsOptimization: report?.needsOptimization || false
  };
}

// Export all
export default {
  detectLanguage,
  inferTaskType,
  calculateSpecificity,
  estimateTokens,
  lintPrompt,
  optimizePrompt,
  getLintSummary
};
