let weSyllableView = 'sounds';

function weLegacySyllablesHtml(w) {
  const groups = {};
  (w.alignment || []).forEach(a => {
    const index = a.syllable != null ? a.syllable : 0;
    (groups[index] = groups[index] || []).push(a);
  });
  return (w.syllables || []).map((s, i) => {
    const units = (groups[i] || []).map(a => {
      const sound = a.silent ? 'silent' : '/' + (phonemeMap[a.og_phoneme_id]?.sound || a.arpabet) + '/';
      return `<div class="pg-bd-unit${a.silent ? ' silent' : ''}"><span class="pg-bd-g">${a.grapheme}</span><span class="pg-bd-p">${sound}</span></div>`;
    }).join('');
    return weSyllableBox(s, units);
  }).join('');
}

function weSyllableBox(syllable, unitsHtml) {
  const color = SYL_TYPE_COLORS[syllable?.type] || '#d8e0d8';
  const label = syllable ? `<div class="pg-syl-type" style="background:${color}"><strong>${syllable.cv}</strong> ${SYL_TYPE_LABELS[syllable.type] || syllable.type}</div>` : '';
  return `<div class="pg-syl" style="border-color:${color};background:${color}22"><div class="pg-syl-units">${unitsHtml}</div>${label}</div>`;
}

function weBreakdownUnitHtml(item) {
  const tail = weMeta[item.concept]?.tail ? ' tail' : '';
  const selected = weFeatures.includes(item.concept) ? ' selected' : '';
  const sounds = weSoundSpansHtml(item.sounds);
  if (!item.concept) return `<div class="pg-bd-unit punct"><span class="pg-bd-g">${item.spelling}</span></div>`;
  return `<div class="pg-bd-unit${tail}${selected}" data-token="${item.concept}">${weGraphemeSpanHtml(item.spelling, 'pg-bd-g')}<span class="pg-bd-p">${sounds}</span></div>`;
}

function weSyllableLabel(w, analysis, index) {
  const agrees = !(analysis.warnings || []).length && (w.syllables || []).length === analysis.syllables.length;
  return agrees ? w.syllables[index] : undefined;
}

function weSyllablesFromAnalysis(w, analysis) {
  const base = analysis.phonograms.filter(item => item.layer === 'base');
  return analysis.syllables.map((_, index) => {
    const units = base.filter(item => item.syllable === index).map(weBreakdownUnitHtml).join('');
    return weSyllableBox(weSyllableLabel(w, analysis, index), units);
  }).join('');
}

function weWarningNoteHtml(analysis) {
  const reasons = (analysis.warnings || []).map(r => weReasonLabels[r] || r);
  if (!reasons.length) return '';
  return `<div class="pg-soft-note">${UI.explorerDisplay.breakdown.warningNote} ${reasons.join('; ')}</div>`;
}

function weNoBreakdownHtml(analysis) {
  const reasons = weShownReasons(analysis?.reasons || []).map(r => weReasonLabels[r] || r).join(' ');
  return `<div class="pg-note">${wePronCopy().noBreakdown} ${reasons}</div>`;
}

function weLetterNamesHtml(w) {
  const copy = UI.explorerDisplay.breakdown;
  const labels = String(w.origins.letter_names).split(', ');
  const units = labels.map((label, index) => `<div class="pg-bd-unit"><span class="pg-bd-g">${w.word[index] ?? ''}</span><span class="pg-bd-p">${label}</span></div>`).join('');
  return `<div class="pg-note">${copy.letterNames}</div><div class="pg-breakdown"><div class="pg-syl"><div class="pg-syl-units">${units}</div></div></div>`;
}

function weAbbreviationHtml(w) {
  if (w.origins?.letter_names) return weLetterNamesHtml(w);
  return `<div class="pg-note">${UI.explorerDisplay.breakdown.abbreviationNote}</div>`;
}

function weBreakdownStackHtml(...parts) {
  return `<div class="pg-bd-stack">${parts.filter(Boolean).join('')}</div>`;
}

function weSyllableBreakdownHtml(w) {
  if (w.origins?.letter_names || (w.origins?.abbreviation !== undefined && w.phonogram_analysis?.status === 'excluded')) return weAbbreviationHtml(w);
  const { analysis, main } = weActiveAnalysis(w);
  const ready = analysis && analysis.status === 'consistent' && analysis.syllables.length;
  const picker = wePronunciationsHtml(w);
  if (!ready && !main) return weBreakdownStackHtml(picker, weNoBreakdownHtml(analysis));
  if (!ready) {
    const note = analysis ? `<div class="pg-note">${UI.explorerDisplay.breakdown.legacyNote}</div>` : '';
    return weBreakdownStackHtml(picker, note, `<div class="pg-breakdown">${weLegacySyllablesHtml(w)}</div>`);
  }
  const written = weHasWrittenView(analysis) && weSyllableView === 'written';
  const toggle = weHasWrittenView(analysis) ? weSyllableViewToggleHtml() : '';
  const body = written ? weSyllablesFromWritten(w, analysis) : weSyllablesFromAnalysis(w, analysis);
  const note = written ? '' : weWarningNoteHtml(analysis);
  return weBreakdownStackHtml(picker, toggle, `<div class="pg-breakdown">${body}</div>`, note);
}
