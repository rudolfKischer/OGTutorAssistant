function wePartLetters(word, item, start, end) {
  return item.spans.map(([from, to]) => word.slice(Math.max(from, start), Math.min(to, end))).join('');
}

function weCrossingUnitHtml(word, item, start, end) {
  const begins = item.spans[0][0] >= start;
  const selected = weFeatures.includes(item.concept) ? ' selected' : '';
  const letters = wePartLetters(word, item, start, end);
  const token = GRAPHEME_TOKEN + item.spelling;
  const sound = begins ? weSoundSpansHtml(item.sounds) : `<span class="pg-cont">↳ ${UI.explorerDisplay.breakdown.continuation}</span>`;
  return `<div class="pg-bd-unit crossing ${begins ? 'primary' : 'cont'}${selected}" data-token="${item.concept}">
    <span class="pg-bd-g" data-token="${token}">${letters}</span><span class="pg-bd-p">${sound}</span></div>`;
}

function weWrittenUnitsHtml(w, analysis, start, end) {
  const base = analysis.phonograms.filter(item => item.layer === 'base')
    .sort((a, b) => a.spans[0][0] - b.spans[0][0]);
  return base.filter(item => item.spans.some(([from, to]) => from < end && to > start)).map(item => {
    const first = item.spans[0][0];
    const last = item.spans[item.spans.length - 1][1];
    return first >= start && last <= end ? weBreakdownUnitHtml(item) : weCrossingUnitHtml(w.word, item, start, end);
  }).join('');
}

function weSyllablesFromWritten(w, analysis) {
  const labelled = (w.syllables || []).length === analysis.written.length;
  return analysis.written.map(([start, end], index) =>
    weSyllableBox(labelled ? w.syllables[index] : undefined, weWrittenUnitsHtml(w, analysis, start, end))).join('');
}

function weHasWrittenView(analysis) {
  const warnings = analysis.warnings || [];
  return warnings.length > 0 && !warnings.includes('syllable_reconstruction') && (analysis.written || []).length > 0;
}

function weSyllableViewToggleHtml() {
  const buttons = UI.explorerDisplay.breakdown.views.map(view =>
    `<button class="pg-seg${view.id === weSyllableView ? ' active' : ''}" title="${view.hint}" onclick="weSetSyllableView('${view.id}')">${view.label}</button>`).join('');
  return `<div class="pg-bd-controls"><span class="pg-segs">${buttons}</span></div>`;
}

window.weSetSyllableView = function(view) {
  weSyllableView = view;
  weRerenderDetail();
};
