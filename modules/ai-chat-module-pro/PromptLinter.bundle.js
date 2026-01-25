/**
 * PromptLinter.bundle.js
 * Browser-compatible IIFE bundle for prompt analysis and optimization
 * 
 * Usage: <script src="PromptLinter.bundle.js"></script>
 * Access via: window.PromptLinter.lintPrompt(text)
 */
(function(global) {
  'use strict';

  // ============================================================
  // LANGUAGE DETECTION
  // ============================================================

  const FR_PATTERNS = [
    /\b(créer|crée|créez|génère|générer|écris|écrire|modifier|ajouter|supprimer)\b/i,
    /\b(avec|pour|dans|sur|une?|les?|des?|mon|ma|mes|ce|cette)\b/i,
    /\b(fichier|page|jeu|projet|application|fonction)\b/i,
    /\b(s'il vous plaît|svp|merci)\b/i,
  ];

  const EN_PATTERNS = [
    /\b(create|generate|write|modify|add|delete|remove|build|make|fix)\b/i,
    /\b(with|for|the|a|an|my|this|that)\b/i,
    /\b(file|page|game|project|application|function|component)\b/i,
    /\b(please|thanks)\b/i,
  ];

  function detectLanguage(text) {
    const frScore = FR_PATTERNS.filter(p => p.test(text)).length;
    const enScore = EN_PATTERNS.filter(p => p.test(text)).length;
    return frScore > enScore ? 'fr' : 'en';
  }

  // ============================================================
  // TASK TYPE INFERENCE
  // ============================================================

  const TASK_PATTERNS = {
    fix: {
      en: /\b(fix|debug|solve|resolve|repair|patch)\b/i,
      fr: /\b(corriger|réparer|résoudre|debugger|fixer)\b/i,
      output: 'code'
    },
    create: {
      en: /\b(create|generate|write|build|make|new)\b/i,
      fr: /\b(créer|crée|génère|générer|écris|écrire|construire|nouveau)\b/i,
      output: 'file'
    },
    modify: {
      en: /\b(modify|change|update|edit|improve|refactor|adjust)\b/i,
      fr: /\b(modifier|changer|mettre à jour|éditer|améliorer|ajuster)\b/i,
      output: 'diff'
    },
    explain: {
      en: /\b(explain|describe|what is|how does|tell me|how to)\b/i,
      fr: /\b(explique|expliquer|décris|décrire|c'est quoi|comment)\b/i,
      output: 'text'
    },
    analyze: {
      en: /\b(analyze|review|check|audit|evaluate|inspect)\b/i,
      fr: /\b(analyser|analyse|vérifier|évaluer|examiner|inspecter)\b/i,
      output: 'report'
    }
  };

  function inferTaskType(text, lang) {
    lang = lang || 'en';
    for (const [type, config] of Object.entries(TASK_PATTERNS)) {
      const pattern = config[lang] || config.en;
      if (pattern.test(text)) {
        return { type: type, output: config.output, confidence: 0.8 };
      }
    }
    return { type: 'unknown', output: 'unknown', confidence: 0.3 };
  }

  // ============================================================
  // SPECIFICITY SCORING
  // ============================================================

  function calculateSpecificity(text, lang) {
    lang = lang || 'en';
    let score = 50;
    const suggestions = [];
    const wordCount = text.split(/\s+/).length;

    // Word count scoring
    if (wordCount > 20) score += 15;
    else if (wordCount > 10) score += 8;
    else if (wordCount < 5) {
      score -= 20;
      suggestions.push(lang === 'fr' 
        ? 'Ajoutez plus de détails' 
        : 'Add more details');
    }

    // Technical terms bonus
    const techTerms = [
      /\b(html|css|javascript|python|react|vue|api|json|database|server)\b/i,
      /\b(function|class|method|variable|array|object|loop)\b/i,
      /\b(responsive|mobile|desktop|animation|style)\b/i
    ];
    score += Math.min(techTerms.filter(p => p.test(text)).length * 5, 20);

    // Numbers bonus
    if (/\b\d+\b/.test(text)) {
      score += 10;
    } else {
      suggestions.push(lang === 'fr'
        ? 'Ajoutez des nombres spécifiques'
        : 'Add specific numbers');
    }

    // File extension bonus
    if (/\.\w{2,4}\b/.test(text)) score += 10;

    // Color/dimension bonus
    if (/(#[0-9a-f]{3,6}|\b\d+px\b|\brgb|\brem\b)/i.test(text)) score += 5;

    // Vague words penalty
    const vagueCount = (text.match(/\b(something|stuff|thing|some|maybe|probably|etc)\b/gi) || []).length;
    score -= vagueCount * 8;
    if (vagueCount > 0) {
      suggestions.push(lang === 'fr'
        ? 'Remplacez les mots vagues'
        : 'Replace vague words');
    }

    return {
      score: Math.max(0, Math.min(100, score)),
      wordCount: wordCount,
      suggestions: suggestions
    };
  }

  // ============================================================
  // TOKEN ESTIMATION
  // ============================================================

  function estimateTokens(text, taskType) {
    const charCount = text.length;
    const hasCode = /```|function|class|def |import /.test(text);
    const charsPerToken = hasCode ? 3 : 4;
    const inputTokens = Math.ceil(charCount / charsPerToken);

    const outputMultipliers = {
      create: 15, modify: 5, explain: 8,
      analyze: 10, fix: 6, unknown: 8
    };
    const outputTokens = inputTokens * (outputMultipliers[taskType] || 8);

    // Claude Sonnet pricing
    const inputCost = (inputTokens / 1000) * 0.003;
    const outputCost = (outputTokens / 1000) * 0.015;

    return {
      input: inputTokens,
      output: outputTokens,
      cost: (inputCost + outputCost).toFixed(4)
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
      message: { en: 'Negation detected (often ignored by LLMs)', fr: 'Négation détectée (souvent ignorée)' },
      fix: { en: 'Reframe positively', fr: 'Reformuler positivement' }
    },
    conflict: {
      patterns: {
        en: [/\b(short|brief)\b.{0,30}\b(detailed|comprehensive|thorough)\b/i, /\b(simple)\b.{0,30}\b(complex|advanced)\b/i],
        fr: [/\b(court|bref)\b.{0,30}\b(détaillé|complet)\b/i, /\b(simple)\b.{0,30}\b(complexe|avancé)\b/i]
      },
      severity: 'high',
      message: { en: 'Conflicting instructions', fr: 'Instructions contradictoires' },
      fix: { en: 'Choose one direction', fr: 'Choisir une direction' }
    },
    vague: {
      patterns: {
        en: [/\bthe\s+code\b/i, /\bmy\s+project\b/i, /\bthis\s+thing\b/i, /\bthat\s+stuff\b/i],
        fr: [/\ble\s+code\b/i, /\bmon\s+projet\b/i, /\bcette\s+chose\b/i, /\bce\s+truc\b/i]
      },
      severity: 'medium',
      message: { en: 'Vague reference', fr: 'Référence vague' },
      fix: { en: 'Be more specific', fr: 'Être plus spécifique' }
    },
    ambiguous: {
      patterns: {
        en: [/\bsome\s+\w+/i, /\ba\s+few\s+\w+/i, /\bseveral\s+\w+/i, /\bmany\s+\w+/i],
        fr: [/\bquelques\s+\w+/i, /\bplusieurs\s+\w+/i, /\bbeaucoup\s+de\b/i]
      },
      severity: 'low',
      message: { en: 'Ambiguous quantity', fr: 'Quantité ambiguë' },
      fix: { en: 'Specify exact number', fr: 'Préciser le nombre' }
    },
    implicit: {
      patterns: {
        en: [/\blike before\b/i, /\bas usual\b/i, /\byou know\b/i, /\bthe same\b/i],
        fr: [/\bcomme avant\b/i, /\bcomme d'habitude\b/i, /\btu sais\b/i, /\bpareil\b/i]
      },
      severity: 'medium',
      message: { en: 'Implicit assumption', fr: 'Hypothèse implicite' },
      fix: { en: 'Define context explicitly', fr: 'Définir le contexte' }
    },
    missingFormat: {
      patterns: {
        en: [/^(?!.*\b(html|json|python|react|file|markdown|csv|xml)\b).{20,}(create|generate|write|make)/i],
        fr: [/^(?!.*\b(html|json|python|react|fichier|markdown|csv|xml)\b).{20,}(créer|génère|écris|faire)/i]
      },
      severity: 'low',
      message: { en: 'No output format specified', fr: 'Format de sortie non spécifié' },
      fix: { en: 'Specify format (HTML, JSON, etc.)', fr: 'Spécifier le format' }
    },
    tooComplex: {
      patterns: {
        en: [/\band\s+then\b.*\band\s+then\b/i, /\bfirst\b.*\bthen\b.*\bfinally\b/i, /\balso\b.*\balso\b.*\balso\b/i],
        fr: [/\bet\s+puis\b.*\bet\s+puis\b/i, /\bd'abord\b.*\bensuite\b.*\bfinalement\b/i]
      },
      severity: 'high',
      message: { en: 'Multiple steps detected', fr: 'Plusieurs étapes détectées' },
      fix: { en: 'Split into separate requests', fr: 'Diviser en requêtes séparées' }
    }
  };

  // ============================================================
  // OPTIMIZATION ENGINE
  // ============================================================

  function optimizePrompt(text, lang) {
    let optimized = text;

    // 1. REFRAME NEGATIONS - expanded patterns
    if (lang === 'fr') {
      // Specific patterns
      optimized = optimized.replace(/\bne\s+pas\s+utiliser\s+de\s+boucles?\b/gi, 'utiliser des list comprehensions');
      optimized = optimized.replace(/\bpas\s+de\s+boucles?\b/gi, 'utiliser des list comprehensions');
      optimized = optimized.replace(/\bpas\s+de\s+commentaires?\b/gi, 'code auto-documenté');
      optimized = optimized.replace(/\bpas\s+trop\s+long\b/gi, 'concis (max 100 lignes)');
      optimized = optimized.replace(/\bpas\s+de\s+bullet\s*points?\b/gi, 'utiliser des paragraphes');
      optimized = optimized.replace(/\bsans\s+dépendances?\b/gi, 'bibliothèque standard uniquement');
      optimized = optimized.replace(/\bsans\s+erreurs?\b/gi, 'avec gestion robuste des erreurs');
      optimized = optimized.replace(/\bsans\s+bugs?\b/gi, 'avec tests unitaires');
      // Generic negations
      optimized = optimized.replace(/\bn['']?utilise\s+pas\s+(\w+)/gi, 'préférer une alternative à $1');
      optimized = optimized.replace(/\bne\s+pas\s+faire\b/gi, 'éviter de faire');
      optimized = optimized.replace(/\béviter\s+les?\s+(\w+)/gi, 'minimiser les $1');
      optimized = optimized.replace(/\béviter\s+de\b/gi, 'minimiser');
      optimized = optimized.replace(/\bjamais\s+de\s+(\w+)/gi, 'aucun $1 (strict)');
      optimized = optimized.replace(/\bjamais\s+(\w+)/gi, 'strictement pas de $1');
    } else {
      // Specific patterns
      optimized = optimized.replace(/\bdon'?t\s+use\s+loops?\b/gi, 'use list comprehensions or functional methods');
      optimized = optimized.replace(/\bdon'?t\s+add\s+comments?\b/gi, 'write self-documenting code');
      optimized = optimized.replace(/\bdon'?t\s+make\s+it\s+long\b/gi, 'keep concise (max 100 lines)');
      optimized = optimized.replace(/\bdon'?t\s+use\s+bullet\s*points?\b/gi, 'use prose paragraphs');
      optimized = optimized.replace(/\bwithout\s+dependencies\b/gi, 'using only standard library');
      optimized = optimized.replace(/\bwithout\s+errors?\b/gi, 'with robust error handling');
      optimized = optimized.replace(/\bwithout\s+bugs?\b/gi, 'with unit tests');
      // Generic negations
      optimized = optimized.replace(/\bavoid\s+errors?\b/gi, 'implement robust error handling');
      optimized = optimized.replace(/\bavoid\s+bugs?\b/gi, 'include defensive coding practices');
      optimized = optimized.replace(/\bavoid\s+(\w+)/gi, 'minimize $1');
      optimized = optimized.replace(/\bno\s+external\s+(\w+)/gi, 'use only built-in $1');
      optimized = optimized.replace(/\bno\s+(\w+)\s+allowed/gi, 'strictly exclude $1');
      optimized = optimized.replace(/\bnot\s+too\s+long\b/gi, 'concise (max 150 words)');
      optimized = optimized.replace(/\bnot\s+too\s+short\b/gi, 'detailed (min 100 words)');
      optimized = optimized.replace(/\bnot\s+too\s+(\w+)/gi, 'moderately $1');
      optimized = optimized.replace(/\bdon'?t\s+use\s+(\w+)/gi, 'prefer alternatives to $1');
      optimized = optimized.replace(/\bdon'?t\s+(\w+)/gi, 'avoid $1 - instead');
      optimized = optimized.replace(/\bnever\s+use\s+(\w+)/gi, 'strictly avoid $1');
      optimized = optimized.replace(/\bnever\s+(\w+)/gi, 'ensure no $1');
      optimized = optimized.replace(/\bno\s+need\s+for\b/gi, 'omit');
    }

    // 2. RESOLVE CONFLICTS - expanded
    if (lang === 'fr') {
      optimized = optimized.replace(/\b(court|bref)\b(.{0,20})\b(détaillé|complet)\b/gi, 'détaillé mais concis (max 200 mots)');
      optimized = optimized.replace(/\b(détaillé|complet)\b(.{0,20})\b(court|bref)\b/gi, 'détaillé mais concis (max 200 mots)');
      optimized = optimized.replace(/\b(simple)\b(.{0,20})\b(complet|exhaustif)\b/gi, 'complet avec structure claire');
      optimized = optimized.replace(/\b(rapide)\b(.{0,20})\b(approfondi)\b/gi, 'efficace et structuré');
    } else {
      optimized = optimized.replace(/\b(short|brief)\b(.{0,20})\b(detailed|comprehensive)\b/gi, 'detailed but concise (max 200 words)');
      optimized = optimized.replace(/\b(detailed|comprehensive)\b(.{0,20})\b(short|brief)\b/gi, 'detailed but concise (max 200 words)');
      optimized = optimized.replace(/\b(simple)\b(.{0,20})\b(comprehensive|thorough)\b/gi, 'comprehensive with clear structure');
      optimized = optimized.replace(/\b(quick)\b(.{0,20})\b(thorough|in-depth)\b/gi, 'efficient and structured');
      optimized = optimized.replace(/\b(basic)\b(.{0,20})\b(advanced)\b/gi, 'progressive from basic to advanced');
    }

    // 3. CLARIFY VAGUE REFERENCES - expanded
    if (/\bmy project\b/i.test(optimized) && !/\bcurrent\b/i.test(optimized)) {
      optimized = optimized.replace(/\bmy project\b/gi, 'my current project');
    }
    if (/\bmon projet\b/i.test(optimized) && !/\bactuel\b/i.test(optimized)) {
      optimized = optimized.replace(/\bmon projet\b/gi, 'mon projet actuel');
    }
    if (/\bthe code\b/i.test(optimized) && !/\bfile|source|above|below\b/i.test(optimized)) {
      optimized = optimized.replace(/\bthe code\b/gi, 'the code provided above');
    }
    if (/\ble code\b/i.test(optimized) && !/\bfichier|source|ci-dessus\b/i.test(optimized)) {
      optimized = optimized.replace(/\ble code\b/gi, 'le code ci-dessus');
    }
    optimized = optimized.replace(/\bthis thing\b/gi, 'this specific element');
    optimized = optimized.replace(/\bthat stuff\b/gi, 'the mentioned content');
    optimized = optimized.replace(/\bcette chose\b/gi, 'cet élément spécifique');
    optimized = optimized.replace(/\bce truc\b/gi, 'cet élément');

    // 4. ADD SCOPE HINTS - expanded
    optimized = optimized.replace(/\bsome\s+(\w+)/gi, '3-5 $1');
    optimized = optimized.replace(/\ba few\s+(\w+)/gi, '2-3 $1');
    optimized = optimized.replace(/\bseveral\s+(\w+)/gi, '4-6 $1');
    optimized = optimized.replace(/\bmany\s+(\w+)/gi, '8-10 $1');
    optimized = optimized.replace(/\blots of\s+(\w+)/gi, '10+ $1');
    optimized = optimized.replace(/\bquelques\s+(\w+)/gi, '3-5 $1');
    optimized = optimized.replace(/\bplusieurs\s+(\w+)/gi, '4-6 $1');
    optimized = optimized.replace(/\bbeaucoup\s+de\s+(\w+)/gi, '8-10 $1');
    optimized = optimized.replace(/\bun peu de\s+(\w+)/gi, '2-3 $1');

    // 5. REMOVE IMPLICIT ASSUMPTIONS
    optimized = optimized.replace(/\blike before\b/gi, '(specify the previous format)');
    optimized = optimized.replace(/\bas usual\b/gi, '(specify the standard approach)');
    optimized = optimized.replace(/\byou know\b/gi, '');
    optimized = optimized.replace(/\bthe same\b/gi, 'identical to the previous');
    optimized = optimized.replace(/\bcomme avant\b/gi, '(préciser le format précédent)');
    optimized = optimized.replace(/\bcomme d'habitude\b/gi, '(préciser l\'approche standard)');
    optimized = optimized.replace(/\btu sais\b/gi, '');
    optimized = optimized.replace(/\bpareil\b/gi, 'identique au précédent');

    // 6. ADD FORMAT SPEC if missing and creating something
    const createPattern = /\b(create|generate|write|build|make|créer|génère|génerer|écris|faire|fais)\b/i;
    const formatPattern = /\b(html|json|python|react|markdown|file|fichier|csv|xml|yaml|typescript|javascript)\b/i;
    if (createPattern.test(optimized) && !formatPattern.test(optimized)) {
      optimized += lang === 'fr'
        ? '\n\nFormat attendu: fichier HTML complet avec CSS/JS intégrés, ou préciser le format souhaité.'
        : '\n\nExpected format: single HTML file with embedded CSS/JS, or specify preferred format.';
    }

    // 7. CLEAN UP - remove double spaces, trim
    optimized = optimized.replace(/\s{2,}/g, ' ').trim();

    return optimized;
  }

  // ============================================================
  // MAIN LINTER FUNCTION
  // ============================================================

  function lintPrompt(text) {
    if (!text || typeof text !== 'string') {
      return { score: 0, issues: [], lang: 'en', taskType: 'unknown', tokens: { input: 0, output: 0, cost: '0.0000' }, optimized: text || '' };
    }

    const lang = detectLanguage(text);
    const task = inferTaskType(text, lang);
    const specificity = calculateSpecificity(text, lang);
    const tokens = estimateTokens(text, task.type);
    const issues = [];

    // Run all lint rules
    for (const [name, rule] of Object.entries(LINT_RULES)) {
      const patterns = rule.patterns[lang] || rule.patterns.en || [];
      for (const pattern of patterns) {
        if (pattern.test(text)) {
          issues.push({
            type: name,
            severity: rule.severity,
            message: rule.message[lang] || rule.message.en,
            fix: rule.fix[lang] || rule.fix.en
          });
          break;
        }
      }
    }

    // Calculate score
    const severityWeights = { high: 20, medium: 10, low: 5 };
    const penalty = issues.reduce((acc, i) => acc + (severityWeights[i.severity] || 5), 0);
    const baseScore = Math.floor((specificity.score + 100) / 2);
    const score = Math.max(0, Math.min(100, baseScore - penalty));

    // Generate optimized prompt
    const optimized = optimizePrompt(text, lang);

    return {
      lang: lang,
      taskType: task.type,
      taskOutput: task.output,
      confidence: task.confidence,
      specificity: specificity.score,
      tokens: tokens,
      issues: issues,
      score: score,
      optimized: optimized,
      suggestions: specificity.suggestions,
      needsOptimization: score < 70 || optimized !== text
    };
  }

  // ============================================================
  // UTILITY FUNCTIONS
  // ============================================================

  function getSummary(text) {
    const r = lintPrompt(text);
    const icons = { high: '🔴', medium: '🟡', low: '🟢' };
    
    let s = `Score: ${r.score}/100 | ${r.lang.toUpperCase()} | ${r.taskType}\n`;
    s += `Tokens: ~${r.tokens.input}→${r.tokens.output} | Cost: $${r.tokens.cost}\n`;
    
    if (r.issues.length > 0) {
      s += 'Issues: ' + r.issues.map(i => `${icons[i.severity]} ${i.message}`).join(', ');
    }
    
    return s;
  }

  // ============================================================
  // EXPORT TO GLOBAL
  // ============================================================

  global.PromptLinter = {
    lintPrompt: lintPrompt,
    detectLanguage: detectLanguage,
    inferTaskType: inferTaskType,
    calculateSpecificity: calculateSpecificity,
    estimateTokens: estimateTokens,
    optimizePrompt: optimizePrompt,
    getSummary: getSummary,
    VERSION: '1.0.0'
  };

})(typeof window !== 'undefined' ? window : this);
