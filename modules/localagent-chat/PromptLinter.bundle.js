/**
 * PromptLinter.bundle.js v8.0
 * 
 * Three-stage matching with Case Context:
 * 1. Load Case Context (framework, methodology, jurisdiction)
 * 2. Match prompt against skill TRIGGERS with weighted scoring
 * 3. Match prompt against REWRITE PATTERNS, adapting to case context
 */
(function(global) {
  'use strict';

  const API_BASE = 'http://localhost:9998';
  
  let _skills = [];
  let _skillTriggers = {};   // {skillName: {core: [], strong: [], weak: []}}
  let _skillRewrites = {};   // {skillName: [{patterns, template}]}
  let _caseContext = null;   // Active case context
  let _loaded = false;

  // ============================================================
  // CASE CONTEXT
  // ============================================================

  async function loadCaseContext() {
    try {
      const resp = await fetch(API_BASE + '/api/skills/context');
      if (resp.ok) {
        const data = await resp.json();
        _caseContext = data.skill_context || null;
        console.log('[Linter] Case context loaded:', _caseContext?.case_id || 'none');
      }
    } catch (e) {
      console.warn('[Linter] Could not load case context');
      _caseContext = null;
    }
    return _caseContext;
  }

  function getCaseContext() {
    return _caseContext;
  }

  async function setCaseContext(caseData) {
    try {
      const resp = await fetch(API_BASE + '/api/skills/context/from-case', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(caseData)
      });
      if (resp.ok) {
        const data = await resp.json();
        _caseContext = data.context || null;
        console.log('[Linter] Case context synced:', _caseContext?.case_id);
        return true;
      }
    } catch (e) {
      console.warn('[Linter] Could not sync case context');
    }
    return false;
  }

  // ============================================================
  // SKILLS LOADING
  // ============================================================

  async function loadSkills() {
    if (_loaded) return _skills;
    
    // Load case context first
    await loadCaseContext();
    
    try {
      const resp = await fetch(API_BASE + '/api/skills');
      if (!resp.ok) throw new Error('Failed to fetch skills');
      
      const data = await resp.json();
      _skills = data.skills || [];
      
      // Load full details for each skill
      for (const skill of _skills) {
        try {
          const detailResp = await fetch(API_BASE + '/api/skills/' + skill.name);
          if (detailResp.ok) {
            const details = await detailResp.json();
            
            // Parse weighted triggers from description
            const triggers = parseTriggersWeighted(details.description);
            var totalTriggers = triggers.core.length + triggers.strong.length + triggers.weak.length;
            if (totalTriggers > 0) {
              _skillTriggers[skill.name] = triggers;
            }
            
            // Parse rewrites from body
            if (details.body) {
              const rewrites = parseRewrites(details.body);
              if (rewrites.length > 0) {
                _skillRewrites[skill.name] = rewrites;
              }
            }
            
            console.log('[Linter] ' + skill.name + ': ' + totalTriggers + ' triggers (C:' + triggers.core.length + ' S:' + triggers.strong.length + ' W:' + triggers.weak.length + '), ' + 
                        (_skillRewrites[skill.name] ? _skillRewrites[skill.name].length : 0) + ' rewrites');
          }
        } catch (e) {
          console.warn('[Linter] Failed to load skill ' + skill.name + ':', e);
        }
      }
      
      _loaded = true;
      console.log('[Linter] Loaded ' + Object.keys(_skillTriggers).length + ' skills');
    } catch (e) {
      console.warn('[Linter] Failed to fetch skills:', e);
    }
    return _skills;
  }

  /**
   * Parse "Triggers:" line from skill description
   */
  function parseTriggers(description) {
    if (!description) return [];
    
    // Find "Triggers:" line
    const match = description.match(/Triggers?:\s*([^\n]+(?:\n(?![A-Z][a-z]*:)[^\n]+)*)/i);
    if (!match) return [];
    
    // Split by comma and clean up
    const triggersText = match[1].replace(/\n/g, ' ');
    const triggers = triggersText.split(',').map(function(t) {
      return t.trim().toLowerCase();
    }).filter(function(t) {
      return t.length > 1;
    });
    
    return triggers;
  }

  /**
   * Parse "Triggers-Core:", "Triggers-Strong:", "Triggers-Weak:" from skill description
   * Returns: { core: [...], strong: [...], weak: [...] }
   */
  function parseTriggersWeighted(description) {
    if (!description) return { core: [], strong: [], weak: [] };
    
    var result = { core: [], strong: [], weak: [] };
    
    // Parse each category
    var categories = ['Core', 'Strong', 'Weak'];
    for (var i = 0; i < categories.length; i++) {
      var cat = categories[i];
      var regex = new RegExp('Triggers-' + cat + ':\\s*([^\\n]+(?:\\n(?![A-Z][a-z]*[-:])[^\\n]+)*)', 'i');
      var match = description.match(regex);
      if (match) {
        var triggersText = match[1].replace(/\n/g, ' ');
        var triggers = triggersText.split(',').map(function(t) {
          return t.trim().toLowerCase();
        }).filter(function(t) {
          return t.length > 1;
        });
        result[cat.toLowerCase()] = triggers;
      }
    }
    
    // Fallback: if no categorized triggers, use old parseTriggers
    if (result.core.length === 0 && result.strong.length === 0 && result.weak.length === 0) {
      var oldTriggers = parseTriggers(description);
      result.strong = oldTriggers;
    }
    
    return result;
  }

  /**
   * Parse "## Prompt Rewrites" section from SKILL.md body
   */
  function parseRewrites(body) {
    const rewrites = [];
    
    if (!body || typeof body !== 'string') return rewrites;
    
    // Find "## Prompt Rewrites" section - stop at next ## header
    const sectionMatch = body.match(/## Prompt Rewrites\s*\n([\s\S]*?)(?=\n## [A-Za-z]|$)/i);
    if (!sectionMatch) return rewrites;
    
    const content = sectionMatch[1];
    
    // Find all ### blocks with ```
    const blockRegex = /###\s+([^\n]+)\n```(?:[^\n]*)?\n([\s\S]*?)```/g;
    let match;
    
    while ((match = blockRegex.exec(content)) !== null) {
      const patternLine = match[1].trim();
      const template = match[2].trim();
      
      if (!patternLine || !template) continue;
      
      // Split patterns by |
      const patterns = patternLine.split('|').map(function(p) {
        return p.trim().toLowerCase();
      }).filter(function(p) {
        return p.length > 0;
      });
      
      if (patterns.length === 0) continue;
      
      rewrites.push({
        patterns: patterns,
        template: template
      });
    }
    
    return rewrites;
  }

  // ============================================================
  // MATCHING
  // ============================================================

  // Weights for trigger categories
  var TRIGGER_WEIGHTS = { core: 20, strong: 10, weak: 3 };

  /**
   * Match prompt against skill triggers with weighted scoring
   * Returns: [{skill, score, matchedTriggers}]
   */
  function matchSkills(text) {
    var textLower = text.toLowerCase();
    var matches = [];
    
    for (var skillName in _skillTriggers) {
      if (!_skillTriggers.hasOwnProperty(skillName)) continue;
      
      var triggers = _skillTriggers[skillName];
      var score = 0;
      var matchedTriggers = [];
      
      // Check each category with different weights
      var categories = ['core', 'strong', 'weak'];
      for (var c = 0; c < categories.length; c++) {
        var category = categories[c];
        var weight = TRIGGER_WEIGHTS[category];
        var categoryTriggers = triggers[category] || [];
        
        for (var i = 0; i < categoryTriggers.length; i++) {
          var trigger = categoryTriggers[i];
          // Create regex for trigger (word boundary, allow flexible spaces)
          var escaped = trigger.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          escaped = escaped.replace(/\s+/g, '\\s*');
          var regex = new RegExp('\\b' + escaped + '\\b', 'i');
          
          if (regex.test(textLower)) {
            score += weight;
            matchedTriggers.push({ trigger: trigger, category: category, weight: weight });
          }
        }
      }
      
      if (score > 0) {
        matches.push({
          skill: skillName,
          score: score,
          matchedTriggers: matchedTriggers
        });
      }
    }
    
    // Sort by score descending
    matches.sort(function(a, b) { return b.score - a.score; });
    
    return matches;
  }

  /**
   * Get best rewrite for a skill based on prompt
   */
  function getBestRewrite(skillName, text) {
    var rewrites = _skillRewrites[skillName];
    if (!rewrites || rewrites.length === 0) return null;
    
    var textLower = text.toLowerCase();
    var bestMatch = null;
    var bestScore = 0;
    
    for (var i = 0; i < rewrites.length; i++) {
      var rewrite = rewrites[i];
      var score = 0;
      var matchedPatterns = [];
      
      for (var j = 0; j < rewrite.patterns.length; j++) {
        var pattern = rewrite.patterns[j];
        var escaped = pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        escaped = escaped.replace(/\s+/g, '\\s*');
        var regex = new RegExp('\\b' + escaped + '\\b', 'i');
        
        if (regex.test(textLower)) {
          score += pattern.length;
          matchedPatterns.push(pattern);
        }
      }
      
      if (score > bestScore) {
        bestScore = score;
        bestMatch = {
          skill: skillName,
          patterns: matchedPatterns,
          template: rewrite.template,
          score: score
        };
      }
    }
    
    // If no pattern matched, return first rewrite as default
    if (!bestMatch && rewrites.length > 0) {
      bestMatch = {
        skill: skillName,
        patterns: [rewrites[0].patterns[0]],
        template: rewrites[0].template,
        score: 1
      };
    }
    
    // Apply case context substitution if available
    if (bestMatch && _caseContext) {
      bestMatch.template = applyContextToTemplate(bestMatch.template, _caseContext);
      bestMatch.contextApplied = true;
    }
    
    return bestMatch;
  }

  /**
   * Apply case context to a template
   * Handles: {{variable}}, {{#if condition}}...{{/if}}
   */
  function applyContextToTemplate(template, context) {
    if (!template || !context) return template;
    
    var result = template;
    
    // 1. Handle conditionals: {{#if condition}}content{{/if}}
    var ifRegex = /\{\{#if\s+(\w+)\}\}([\s\S]*?)\{\{\/if\}\}/g;
    result = result.replace(ifRegex, function(match, condition, content) {
      // Check if condition is truthy in context
      if (context[condition]) {
        return content;
      }
      return '';
    });
    
    // 2. Handle simple variable substitution: {{variable}}
    var varRegex = /\{\{(\w+)\}\}/g;
    result = result.replace(varRegex, function(match, varName) {
      if (context.hasOwnProperty(varName) && context[varName]) {
        return context[varName];
      }
      return match; // Keep placeholder if not found
    });
    
    // 3. Clean up empty lines from removed conditionals
    result = result.replace(/\n\s*\n\s*\n/g, '\n\n');
    
    return result;
  }

  /**
   * Get all matching rewrites across skills
   */
  function matchRewrites(text) {
    var skillMatches = matchSkills(text);
    var rewrites = [];
    
    for (var i = 0; i < skillMatches.length; i++) {
      var skillMatch = skillMatches[i];
      var rewrite = getBestRewrite(skillMatch.skill, text);
      if (rewrite) {
        rewrite.skillScore = skillMatch.score;
        rewrite.matchedTriggers = skillMatch.matchedTriggers;
        rewrites.push(rewrite);
      }
    }
    
    return rewrites;
  }

  // ============================================================
  // LANGUAGE & TASK DETECTION
  // ============================================================

  function detectLanguage(text) {
    var frPatterns = [/\b(créer|génère|analyser|délai|retard|réclamation|contrat)\b/i];
    var frScore = 0;
    for (var i = 0; i < frPatterns.length; i++) {
      if (frPatterns[i].test(text)) frScore++;
    }
    return frScore > 0 ? 'fr' : 'en';
  }

  var TASK_PATTERNS = {
    fix: /\b(fix|debug|solve|resolve|corriger)\b/i,
    create: /\b(create|generate|write|build|créer|génère|prepare|draft)\b/i,
    modify: /\b(modify|change|update|edit|modifier)\b/i,
    explain: /\b(explain|describe|what|how|expliquer)\b/i,
    analyze: /\b(analyze|review|check|audit|analyser|assess|calculate)\b/i
  };

  function inferTaskType(text) {
    for (var type in TASK_PATTERNS) {
      if (TASK_PATTERNS.hasOwnProperty(type) && TASK_PATTERNS[type].test(text)) {
        return type;
      }
    }
    return 'unknown';
  }

  // ============================================================
  // TOKEN ESTIMATION
  // ============================================================

  function estimateTokens(text, taskType) {
    var input = Math.ceil(text.length / 4);
    var multipliers = { create: 15, modify: 5, explain: 8, analyze: 12, fix: 6, unknown: 8 };
    var output = input * (multipliers[taskType] || 8);
    var cost = Math.round(((input / 1000) * 0.003 + (output / 1000) * 0.015) * 10000) / 10000;
    return { input: input, output: output, cost: cost };
  }

  // ============================================================
  // LINT RULES
  // ============================================================

  var LINT_RULES = {
    negation: {
      pattern: /\b(don'?t|not|never|avoid|ne\s+pas)\b/i,
      severity: 'high',
      message: 'Negations detected',
      fix: 'Reframe positively'
    },
    vagueReference: {
      pattern: /\b(the\s+code|my\s+project|this\s+thing)\b/i,
      severity: 'medium',
      message: 'Vague references',
      fix: 'Be more specific'
    },
    ambiguousScope: {
      pattern: /\b(some|a\s+few|several)\b/i,
      severity: 'low',
      message: 'Ambiguous quantities',
      fix: 'Use specific numbers'
    }
  };

  // ============================================================
  // MAIN LINTER
  // ============================================================

  function lintPrompt(text) {
    if (!text || !text.trim()) {
      return {
        score: 100, lang: 'en', taskType: 'unknown',
        tokens: { input: 0, output: 0, cost: 0 },
        issues: [], rewrites: [], skillMatches: [],
        optimized: text, hasRewrites: false, topRewrite: null
      };
    }
    
    var lang = detectLanguage(text);
    var taskType = inferTaskType(text);
    var tokens = estimateTokens(text, taskType);
    
    // Find issues
    var issues = [];
    for (var name in LINT_RULES) {
      if (LINT_RULES.hasOwnProperty(name)) {
        var rule = LINT_RULES[name];
        if (rule.pattern.test(text)) {
          issues.push({
            type: name,
            severity: rule.severity,
            message: rule.message,
            fix: rule.fix
          });
        }
      }
    }
    
    // Match skills and get rewrites
    var skillMatches = matchSkills(text);
    var rewrites = matchRewrites(text);
    
    // Calculate score
    var weights = { high: 20, medium: 10, low: 5 };
    var penalty = 0;
    for (var i = 0; i < issues.length; i++) {
      penalty += weights[issues[i].severity] || 5;
    }
    var score = 75 - penalty;
    
    var words = text.split(/\s+/).length;
    if (words > 10) score += 10;
    if (words > 20) score += 10;
    if (rewrites.length > 0) score += 5;
    
    score = Math.max(0, Math.min(100, score));
    
    // Basic auto-fix
    var optimized = text
      .replace(/\bsome\b/gi, '3-5')
      .replace(/\ba\s+few\b/gi, '2-3')
      .replace(/\bseveral\b/gi, '4-6');
    
    return {
      score: score,
      lang: lang,
      taskType: taskType,
      tokens: tokens,
      issues: issues,
      skillMatches: skillMatches,
      rewrites: rewrites,
      optimized: optimized,
      hasRewrites: rewrites.length > 0,
      topRewrite: rewrites.length > 0 ? rewrites[0] : null,
      topSkill: skillMatches.length > 0 ? skillMatches[0] : null,
      // Case Context
      caseContext: _caseContext
    };
  }

  async function lintPromptAsync(text) {
    await loadSkills();
    return lintPrompt(text);
  }

  async function activateSkill(skillName) {
    try {
      var resp = await fetch(API_BASE + '/api/skills/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_name: skillName })
      });
      return resp.ok;
    } catch (e) {
      return false;
    }
  }

  // ============================================================
  // LOCAL PROMPT OPTIMIZER — runs entirely in-browser
  // Uses: lint rules, skill triggers, skill rewrites, case context
  // Tiers: beginner (fix issues), intermediate (structured),
  //        advanced (full JSON with case context + methodology)
  // ============================================================

  // Safe negation rewrites — only patterns where meaning is unambiguous
  var NEGATION_REWRITES = {
    "not too long": 'concise (max 200 words)',
    "not too short": 'detailed (min 100 words)',
    "without dependencies": 'standard library only',
    "sans dépendances": 'bibliothèque standard uniquement'
  };

  // Negation patterns to FLAG (shown as suggestion, not auto-applied)
  var NEGATION_FLAGS = [
    "don't", "dont", "do not", "don\u2019t",
    "never", "avoid", "not",
    "ne pas", "n'", "pas de", "\u00e9viter", "jamais"
  ];

  var VAGUE_REWRITES = {
    "some": '3-5',
    "a few": '2-3',
    "several": '4-6',
    "many": '8-10',
    "the code": 'the source files',
    "my project": 'the current project',
    "this thing": 'this component',
    "le code": 'les fichiers source',
    "mon projet": 'le projet actuel',
    "cette chose": 'ce composant',
    "quelques": '3-5',
    "plusieurs": '4-6',
    "beaucoup": '8-10'
  };

  var OUTPUT_FORMATS = {
    create: 'Produce a complete, structured document with all sections.',
    analyze: 'Provide a detailed analytical report with findings, methodology, and recommendations.',
    explain: 'Explain clearly with definitions, examples, and key takeaways.',
    fix: 'Identify root cause, provide corrected version, and explain the fix.',
    modify: 'Show modifications with clear before/after comparison.',
    unknown: 'Provide a structured, comprehensive response.'
  };

  /**
   * Improve a prompt locally — no API calls, no network, fully offline.
   *
   * @param {string} prompt - The raw user prompt
   * @param {Object} lintResult - Result from lintPrompt()/lintPromptAsync() (optional)
   * @param {string} tier - 'beginner', 'intermediate', or 'advanced'
   * @returns {{success: boolean, improved: string, source: string, tier: string, changes: string[]}}
   */
  function improvePrompt(prompt, lintResult, tier) {
    tier = tier || 'intermediate';
    if (!prompt || !prompt.trim()) {
      return { success: false, improved: prompt, source: 'local', tier: tier, changes: [] };
    }

    // Run linter if not provided
    if (!lintResult || !lintResult.issues) {
      lintResult = lintPrompt(prompt);
    }

    var improved = prompt.trim();
    var changes = [];
    var lang = lintResult.lang || detectLanguage(prompt);
    var taskType = lintResult.taskType || inferTaskType(prompt);
    var caseCtx = _caseContext || {};

    // =========================================================
    // BEGINNER: Fix lint issues + basic cleanup
    // =========================================================

    // 1a. Safe negation rewrites (unambiguous patterns only)
    for (var neg in NEGATION_REWRITES) {
      if (NEGATION_REWRITES.hasOwnProperty(neg)) {
        var negRegex = new RegExp('\\b' + neg.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'gi');
        if (negRegex.test(improved)) {
          improved = improved.replace(negRegex, NEGATION_REWRITES[neg]);
          changes.push('Reframed: "' + neg + '" \u2192 "' + NEGATION_REWRITES[neg] + '"');
        }
      }
    }

    // 1b. Flag remaining negations (suggest positive framing, don't auto-rewrite)
    for (var fi = 0; fi < NEGATION_FLAGS.length; fi++) {
      var flag = NEGATION_FLAGS[fi];
      var flagRegex = new RegExp('\\b' + flag.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'i');
      if (flagRegex.test(improved)) {
        changes.push('Tip: consider positive framing instead of "' + flag + '"');
        break; // one tip is enough
      }
    }

    // 2. Replace vague references and quantities
    for (var vague in VAGUE_REWRITES) {
      if (VAGUE_REWRITES.hasOwnProperty(vague)) {
        var vagueRegex = new RegExp('\\b' + vague.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'gi');
        if (vagueRegex.test(improved)) {
          improved = improved.replace(vagueRegex, VAGUE_REWRITES[vague]);
          changes.push('Clarified: "' + vague + '" \u2192 "' + VAGUE_REWRITES[vague] + '"');
        }
      }
    }

    // 3. Capitalize first letter
    if (improved.charAt(0) !== improved.charAt(0).toUpperCase()) {
      improved = improved.charAt(0).toUpperCase() + improved.slice(1);
      changes.push('Capitalized first letter');
    }

    // 4. Ensure ends with punctuation
    if (!/[.!?]$/.test(improved.trim())) {
      improved = improved.trim() + '.';
      changes.push('Added ending punctuation');
    }

    // 5. Clean excessive whitespace (preserve intentional line breaks)
    var cleaned = improved.replace(/[ \t]{2,}/g, ' ').replace(/\n{3,}/g, '\n\n');
    if (cleaned !== improved) {
      improved = cleaned;
      changes.push('Cleaned whitespace');
    }

    if (tier === 'beginner') {
      return { success: true, improved: improved, source: 'local', tier: tier, changes: changes };
    }

    // =========================================================
    // INTERMEDIATE: Add structure + context + output format
    // =========================================================

    var sections = [];
    var taskLabel = (typeof taskType === 'string' ? taskType : taskType).toUpperCase();

    // Skip structuring if prompt already has TASK/OUTPUT headers
    var alreadyStructured = /^TASK:/im.test(improved);
    if (alreadyStructured) {
      // Already structured — only inject context/skill if missing
      if (tier === 'intermediate') {
        return { success: true, improved: improved, source: 'local', tier: tier, changes: changes };
      }
    }

    // Task header
    sections.push('TASK: ' + taskLabel);

    // Case context line
    var ctxParts = [];
    if (caseCtx.framework) ctxParts.push('Framework: ' + caseCtx.framework);
    if (caseCtx.methodology) ctxParts.push('Methodology: ' + caseCtx.methodology);
    if (caseCtx.jurisdiction) ctxParts.push('Jurisdiction: ' + caseCtx.jurisdiction);
    if (caseCtx.forum) ctxParts.push('Forum: ' + caseCtx.forum);
    if (ctxParts.length > 0) {
      sections.push('CONTEXT: ' + ctxParts.join(' | '));
      changes.push('Injected case context (' + ctxParts.length + ' variables)');
    }

    // Active skill reference
    var topSkill = lintResult.topSkill || (lintResult.skillMatches && lintResult.skillMatches[0]) || null;
    if (topSkill) {
      sections.push('SKILL: ' + topSkill.skill + ' (matched ' + topSkill.matchedTriggers.length + ' triggers, score: ' + topSkill.score + ')');
      changes.push('Linked to skill: ' + topSkill.skill);
    }

    // Main prompt body
    sections.push(improved);

    // Output format if not already specified
    if (!/(format|output|return|produce|generate as|respond with)/i.test(improved)) {
      var fmt = OUTPUT_FORMATS[taskType] || OUTPUT_FORMATS['unknown'];
      sections.push('OUTPUT FORMAT: ' + fmt);
      changes.push('Added output format specification');
    }

    // Skill methodology hint
    if (caseCtx.methodology && !new RegExp(caseCtx.methodology, 'i').test(improved)) {
      sections.push('METHODOLOGY: Follow ' + caseCtx.methodology + ' standards and procedures.');
      changes.push('Added methodology reference: ' + caseCtx.methodology);
    }

    improved = sections.join('\n\n');

    if (tier === 'intermediate') {
      return { success: true, improved: improved, source: 'local', tier: tier, changes: changes };
    }

    // =========================================================
    // ADVANCED: Full JSON structure with chain-of-thought
    // =========================================================

    var struct = {};

    // Context block
    var ctx = {};
    if (caseCtx.framework) ctx.framework = caseCtx.framework;
    if (caseCtx.methodology) ctx.methodology = caseCtx.methodology;
    if (caseCtx.jurisdiction) ctx.jurisdiction = caseCtx.jurisdiction;
    if (caseCtx.forum) ctx.forum = caseCtx.forum;
    if (caseCtx.contract_type) ctx.contract_type = caseCtx.contract_type;
    if (caseCtx.dispute_type) ctx.dispute_type = caseCtx.dispute_type;
    if (topSkill) ctx.active_skill = topSkill.skill;
    if (Object.keys(ctx).length > 0) struct.context = ctx;

    // Task block — reuse beginner-cleaned prompt (already has safe rewrites applied)
    struct.task = { type: taskLabel, prompt: improved.replace(/^TASK:.*\n\n/m, '').replace(/\n\nOUTPUT FORMAT:.*$/m, '').trim() };

    // Skill rewrite template if available
    if (lintResult.topRewrite && lintResult.topRewrite.template) {
      struct.skill_template = { skill: lintResult.topRewrite.skill, template: lintResult.topRewrite.template };
      changes.push('Embedded skill rewrite template from ' + lintResult.topRewrite.skill);
    }

    // Constraints
    var constraints = {
      reasoning: 'Think step-by-step. Show your analytical process before conclusions.',
      quality: 'Be precise, cite sources, quantify where possible. Support assertions with evidence.'
    };
    if (caseCtx.methodology) {
      constraints.standards = 'Follow ' + caseCtx.methodology + ' standards, procedures, and documentation requirements.';
    }
    if (caseCtx.forum) {
      constraints.forum = 'Output must be suitable for ' + caseCtx.forum + ' proceedings.';
    }
    struct.constraints = constraints;

    // Output format
    var fmtAdv = OUTPUT_FORMATS[taskType] || OUTPUT_FORMATS['unknown'];
    var outFmt = { structure: fmtAdv, style: 'Professional, evidence-based, suitable for formal proceedings.' };
    if (lang === 'fr') {
      outFmt.language = 'French (formal register)';
    }
    struct.output_format = outFmt;

    improved = JSON.stringify(struct, null, 2);
    changes.push('Generated full JSON-structured prompt');

    return { success: true, improved: improved, source: 'local', tier: tier, changes: changes };
  }

  // ============================================================
  // EXPORT
  // ============================================================

  global.PromptLinter = {
    lintPrompt: lintPrompt,
    lintPromptAsync: lintPromptAsync,
    loadSkills: loadSkills,
    activateSkill: activateSkill,
    detectLanguage: detectLanguage,
    inferTaskType: inferTaskType,
    estimateTokens: estimateTokens,
    // Case Context
    loadCaseContext: loadCaseContext,
    getCaseContext: getCaseContext,
    setCaseContext: setCaseContext,
    // Prompt Improver
    improvePrompt: improvePrompt,
    // Debug
    getSkillTriggers: function() { return _skillTriggers; },
    getSkillRewrites: function() { return _skillRewrites; },
    matchSkills: matchSkills,
    matchRewrites: matchRewrites
  };

})(typeof window !== 'undefined' ? window : this);
