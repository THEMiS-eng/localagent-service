/**
 * PromptLinter.js v2.0
 * 
 * Prompt analysis with dynamic SKILL injection
 * 
 * FEATURES:
 * 1. Language detection (FR/EN)
 * 2. Task type inference (from SKILL or default)
 * 3. Dynamic rules from active SKILL
 * 4. Specificity scoring with skill-aware bonuses
 * 5. Issue detection (negations, conflicts, vague refs)
 * 6. Auto-fix with smart rewrites
 * 7. Token estimation
 * 8. Learning Engine feedback
 */

// ============================================================
// SKILL INTEGRATION
// ============================================================

let _activeSkill = null;
let _skillRules = {};
let _skillPatterns = {};
const API_BASE = 'http://localhost:9998';

/**
 * Fetch active skill from backend
 */
export async function loadActiveSkill() {
  try {
    const resp = await fetch(`${API_BASE}/api/skills/active`);
    if (!resp.ok) return null;
    
    const data = await resp.json();
    if (data.active && data.active.length > 0) {
      const skill = data.active[0];
      _activeSkill = skill;
      
      // Load full skill details
      const detailResp = await fetch(`${API_BASE}/api/skills/${skill.name}`);
      if (detailResp.ok) {
        const details = await detailResp.json();
        _parseSkillRules(details);
      }
      return skill;
    }
  } catch (e) {
    console.warn('[PromptLinter] Failed to load skill:', e);
  }
  return null;
}

/**
 * Parse skill SKILL.md body into rules and patterns
 */
function _parseSkillRules(skillDetails) {
  if (!skillDetails || !skillDetails.body) return;
  
  const body = skillDetails.body;
  _skillRules = {};
  _skillPatterns = {};
  
  // Extract task patterns from skill
  const workflowMatch = body.match(/##\s*(Workflow|Tasks|Analysis Types)[^\n]*\n([\s\S]*?)(?=\n##|$)/i);
  if (workflowMatch) {
    const section = workflowMatch[2];
    const bullets = section.match(/[-*]\s*\*?\*?([^*\n]+)\*?\*?/g) || [];
    bullets.forEach((b, i) => {
      const taskName = b.replace(/[-*\s*]+/g, '').toLowerCase().replace(/[^a-z0-9]/g, '-');
      if (taskName.length > 2) {
        _skillPatterns[taskName] = {
          patterns: [new RegExp(`\\b${taskName.replace(/-/g, '[- ]?')}\\b`, 'i')],
          output: 'report'
        };
      }
    });
  }
  
  // Extract constraints
  const constraintsMatch = body.match(/##\s*Constraints[^\n]*\n([\s\S]*?)(?=\n##|$)/i);
  if (constraintsMatch) {
    const section = constraintsMatch[1];
    const rules = section.match(/[-*]\s*([^\n]+)/g) || [];
    rules.forEach((r, i) => {
      const ruleText = r.replace(/^[-*]\s*/, '').trim();
      if (ruleText.length > 10) {
        _skillRules[`skill_${i}`] = {
          message: { en: ruleText, fr: ruleText },
          severity: ruleText.toLowerCase().includes('must') ? 'high' : 'medium',
          fix: { en: 'Follow skill constraint', fr: 'Respecter la contrainte du skill' }
        };
      }
    });
  }
  
  // Extract domain terms for bonus scoring
  const termsMatch = body.match(/##\s*(Entities|Terms|Domain)[^\n]*\n([\s\S]*?)(?=\n##|$)/i);
  if (termsMatch) {
    const terms = termsMatch[2].match(/`([^`]+)`/g) || [];
    _skillPatterns._domainTerms = terms.map(t => t.replace(/`/g, '').toLowerCase());
  }
}

/**
 * Get active skill info
 */
export function getActiveSkill() {
  return _activeSkill;
}

/**
 * Set skill manually (for testing or external control)
 */
export function setActiveSkill(skill, rules = {}, patterns = {}) {
  _activeSkill = skill;
  _skillRules = rules;
  _skillPatterns = patterns;
}

// ============================================================
// LANGUAGE DETECTION
// ============================================================

const FR_INDICATORS = [
  /\b(créer|crée|créez|génère|générer|écris|écrire|modifier|ajouter|supprimer)\b/i,
  /\b(avec|pour|dans|sur|une?|les?|des?|mon|ma|mes|ce|cette)\b/i,
  /\b(fichier|page|jeu|projet|application|fonction|analyse|délai|retard)\b/i,
  /\b(s'il vous plaît|svp|merci)\b/i,
];

const EN_INDICATORS = [
  /\b(create|generate|write|modify|add|delete|remove|build|make|analyze)\b/i,
  /\b(with|for|the|a|an|my|this|that)\b/i,
  /\b(file|page|game|project|application|function|delay|schedule)\b/i,
  /\b(please|thanks)\b/i,
];

export function detectLanguage(text) {
  const textLower = text.toLowerCase();
  
  const frScore = FR_INDICATORS.filter(p => p.test(textLower)).length;
  const enScore = EN_INDICATORS.filter(p => p.test(textLower)).length;
  
  return frScore > enScore ? 'fr' : 'en';
}

// ============================================================
// TASK TYPE INFERENCE (with SKILL support)
// ============================================================

const DEFAULT_TASK_PATTERNS = {
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
    en: [/\b(analyze|review|check|audit|evaluate|assess)\b/i],
    fr: [/\b(analyser|analyse|vérifier|évaluer|examiner)\b/i],
    output: 'report'
  },
  fix: {
    en: [/\b(fix|debug|solve|resolve|repair)\b/i],
    fr: [/\b(corriger|réparer|résoudre|debugger|fixer)\b/i],
    output: 'code'
  },
  // Construction forensics specific
  'delay-analysis': {
    en: [/\b(delay|schedule|critical\s*path|float|tia|time\s*impact)\b/i],
    fr: [/\b(délai|retard|chemin\s*critique|marge|analyse\s*temps)\b/i],
    output: 'report'
  },
  'rea-preparation': {
    en: [/\b(rea|equitable\s*adjustment|claim|quantum)\b/i],
    fr: [/\b(rea|ajustement|réclamation|quantum)\b/i],
    output: 'document'
  },
  'concurrent-analysis': {
    en: [/\b(concurrent|apportionment|pacing)\b/i],
    fr: [/\b(concurrent|répartition|concomitant)\b/i],
    output: 'report'
  }
};

export function inferTaskType(text, lang = 'en') {
  const textLower = text.toLowerCase();
  
  // First check skill-specific patterns
  if (_activeSkill && Object.keys(_skillPatterns).length > 0) {
    for (const [taskType, config] of Object.entries(_skillPatterns)) {
      if (taskType.startsWith('_')) continue;
      const patterns = config.patterns || [];
      for (const pattern of patterns) {
        if (pattern.test(textLower)) {
          return {
            type: taskType,
            expectedOutput: config.output || 'report',
            confidence: 0.9,
            source: 'skill',
            skill: _activeSkill.name
          };
        }
      }
    }
  }
  
  // Then check default patterns
  for (const [taskType, config] of Object.entries(DEFAULT_TASK_PATTERNS)) {
    const patterns = config[lang] || config.en || [];
    for (const pattern of patterns) {
      if (pattern.test(textLower)) {
        return {
          type: taskType,
          expectedOutput: config.output,
          confidence: 0.8,
          source: 'default'
        };
      }
    }
  }
  
  // No match - return unknown (skill context still applies to rules/scoring)
  return { type: 'unknown', expectedOutput: 'unknown', confidence: 0.3, source: 'none' };
}

// ============================================================
// SPECIFICITY SCORING (with SKILL bonuses)
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
  
  // SKILL domain terms bonus
  if (_skillPatterns._domainTerms && _skillPatterns._domainTerms.length > 0) {
    const textLower = text.toLowerCase();
    const domainMatches = _skillPatterns._domainTerms.filter(t => textLower.includes(t)).length;
    score += Math.min(domainMatches * 8, 25);
  }
  
  // Construction forensics specific terms
  const forensicTerms = [
    /\b(critical\s*path|float|baseline|as-built|tia|rea|delay\s*event)\b/i,
    /\b(concurrent|apportionment|fragnet|window|methodology)\b/i,
    /\b(aace|rp\s*29r|scl\s*protocol|eichleay)\b/i
  ];
  const forensicCount = forensicTerms.filter(p => p.test(text)).length;
  if (forensicCount > 0) {
    score += Math.min(forensicCount * 10, 30);
  }
  
  // Numbers bonus
  if (/\b\d+\b/.test(text)) {
    score += 10;
  } else {
    suggestions.push(lang === 'fr'
      ? 'Ajoutez des nombres spécifiques (ex: "5 jours", "2024-01-15")'
      : 'Add specific numbers (e.g., "5 days", "2024-01-15")');
  }
  
  // Date format bonus (ISO 8601)
  if (/\d{4}-\d{2}-\d{2}/.test(text)) {
    score += 10;
  }
  
  // File extension bonus
  if (/\.\w{2,4}\b/.test(text)) {
    score += 10;
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
    suggestions,
    hasSkillBonus: _activeSkill !== null
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
    analyze: 12,
    fix: 6,
    'delay-analysis': 20,
    'rea-preparation': 25,
    'concurrent-analysis': 18,
    unknown: 8
  };
  const estimatedOutput = inputTokens * (outputMultipliers[task.type] || 8);
  
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
// LINT RULES (Base + Skill)
// ============================================================

const BASE_LINT_RULES = {
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
      en: [/^(?!.*(html|json|python|markdown|file|format|report)).*\b(create|generate|write)\b/i],
      fr: [/^(?!.*(html|json|python|markdown|fichier|format|rapport)).*\b(créer|générer|écrire)\b/i]
    },
    severity: 'medium',
    message: { en: 'Output format not specified', fr: 'Format de sortie non spécifié' },
    fix: { en: 'Specify desired format', fr: 'Spécifier le format souhaité' }
  },
  missingMethodology: {
    patterns: {
      en: [/\b(delay|analysis|claim)\b(?!.*(tia|window|as-built|methodology|aace))/i],
      fr: [/\b(délai|analyse|réclamation)\b(?!.*(tia|fenêtre|tel-que-construit|méthodologie|aace))/i]
    },
    severity: 'medium',
    message: { en: 'No methodology specified', fr: 'Méthodologie non spécifiée' },
    fix: { en: 'Specify analysis methodology (TIA, Windows, etc.)', fr: 'Spécifier la méthodologie (TIA, Fenêtres, etc.)' }
  },
  missingDateFormat: {
    patterns: {
      en: [/\b(date|period|from|to|between)\b(?!.*\d{4}-\d{2}-\d{2})/i],
      fr: [/\b(date|période|du|au|entre)\b(?!.*\d{4}-\d{2}-\d{2})/i]
    },
    severity: 'low',
    message: { en: 'Dates should be ISO 8601 (YYYY-MM-DD)', fr: 'Dates en ISO 8601 (AAAA-MM-JJ)' },
    fix: { en: 'Use ISO 8601 date format', fr: 'Utiliser le format ISO 8601' }
  }
};

function getMergedRules() {
  return { ...BASE_LINT_RULES, ..._skillRules };
}

// ============================================================
// MAIN LINTER FUNCTION
// ============================================================

export function lintPrompt(prompt, options = {}) {
  const lang = detectLanguage(prompt);
  const task = inferTaskType(prompt, lang);
  const specificity = calculateSpecificity(prompt, lang);
  const tokens = estimateTokens(prompt);
  
  const issues = [];
  const promptLower = prompt.toLowerCase();
  
  const rules = getMergedRules();
  
  for (const [ruleName, rule] of Object.entries(rules)) {
    if (!rule.patterns) continue;
    
    const patterns = rule.patterns[lang] || rule.patterns.en || rule.patterns || [];
    const matches = [];
    
    for (const pattern of patterns) {
      if (pattern instanceof RegExp) {
        const found = promptLower.match(pattern);
        if (found) {
          matches.push(...found);
        }
      }
    }
    
    if (matches.length > 0) {
      issues.push({
        type: ruleName,
        severity: rule.severity,
        message: rule.message[lang] || rule.message.en || rule.message,
        matches: [...new Set(matches)].slice(0, 3),
        fix: rule.fix[lang] || rule.fix.en || rule.fix
      });
    }
  }
  
  const severityWeights = { high: 20, medium: 10, low: 5 };
  const issuePenalty = issues.reduce((sum, i) => sum + (severityWeights[i.severity] || 5), 0);
  
  const baseScore = Math.floor((specificity.score + 100) / 2);
  const finalScore = Math.max(0, Math.min(100, baseScore - issuePenalty));
  
  const optimized = optimizePrompt(prompt, issues, lang);
  
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
    needsOptimization: finalScore < 70,
    skill: _activeSkill ? _activeSkill.name : null
  };
}

// ============================================================
// ASYNC LINTER (with skill loading)
// ============================================================

export async function lintPromptAsync(prompt, options = {}) {
  if (!_activeSkill && options.loadSkill !== false) {
    await loadActiveSkill();
  }
  return lintPrompt(prompt, options);
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
      case 'missingMethodology':
        optimized = addMethodologyHint(optimized, lang);
        break;
    }
  }
  
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
    [/\bne\s+pas\s+utiliser\b/gi, 'utiliser uniquement'],
    [/\bpas\s+de\s+commentaires?\b/gi, 'code auto-documenté'],
    [/\bpas\s+trop\s+long\b/gi, 'concis (max 100 lignes)'],
    [/\bsans\s+dépendances?\b/gi, 'bibliothèque standard uniquement'],
  ] : [
    [/\bdon'?t\s+use\b/gi, 'use only'],
    [/\bdon'?t\s+add\s+comments?\b/gi, 'self-documenting code'],
    [/\bwithout\s+dependencies\b/gi, 'standard library only'],
    [/\bavoid\b/gi, 'minimize'],
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
  ] : [
    [/\b(short|brief)\b(.{0,20})\b(detailed|comprehensive)\b/gi, 'detailed (max 200 words)'],
    [/\b(simple)\b(.{0,20})\b(comprehensive)\b/gi, 'comprehensive with clear structure'],
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
    result = result.replace(/\ble\s+code\b/gi, 'les fichiers source');
  } else {
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
        prompt += ' Format: fichier HTML unique.';
      }
    } else {
      if (!/\b(html|json|python|file)\b/i.test(prompt)) {
        prompt += ' Format: single HTML file.';
      }
    }
  }
  return prompt;
}

function addMethodologyHint(prompt, lang = 'en') {
  if (lang === 'fr') {
    prompt += ' Méthodologie: TIA (AACE RP 29R-03).';
  } else {
    prompt += ' Methodology: TIA (AACE RP 29R-03).';
  }
  return prompt;
}

// ============================================================
// LEARNING ENGINE INTEGRATION
// ============================================================

export async function reportToLearning(lintResult, userFeedback = null) {
  try {
    await fetch(`${API_BASE}/api/learning/error`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: 'lint_feedback',
        score: lintResult.score,
        issues: lintResult.issues,
        skill: lintResult.skill,
        feedback: userFeedback,
        timestamp: new Date().toISOString()
      })
    });
  } catch (e) {
    console.warn('[PromptLinter] Failed to report to learning:', e);
  }
}

// ============================================================
// HELPERS
// ============================================================

export function getLintSummary(prompt) {
  const report = lintPrompt(prompt);
  
  const severityIcons = { high: '🔴', medium: '🟡', low: '🟢' };
  
  let summary = `🔍 Score: ${report.score}/100\n`;
  summary += `   Lang: ${report.language.toUpperCase()} | Task: ${report.taskType.type}\n`;
  summary += `   Tokens: ~${report.tokens.inputTokens} in / ~${report.tokens.estimatedOutputTokens} out\n`;
  summary += `   Cost: $${report.tokens.estimatedCost}\n`;
  
  if (report.skill) {
    summary += `   Skill: ${report.skill}\n`;
  }
  
  if (report.issues.length > 0) {
    summary += `\n   Issues (${report.issues.length}):\n`;
    for (const issue of report.issues) {
      const icon = severityIcons[issue.severity] || '⚪';
      summary += `   ${icon} ${issue.message}\n`;
    }
  }
  
  return summary;
}

// ============================================================
// EXPORTS
// ============================================================

export default {
  detectLanguage,
  inferTaskType,
  calculateSpecificity,
  estimateTokens,
  lintPrompt,
  lintPromptAsync,
  optimizePrompt,
  getLintSummary,
  loadActiveSkill,
  getActiveSkill,
  setActiveSkill,
  reportToLearning
};
