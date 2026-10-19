function weShownReasons(reasons) {
  const redundant = new Set(reasons.flatMap(reason => weRedundantReasons[reason] || []));
  return reasons.filter(reason => !redundant.has(reason));
}

function weExclusionHtml(analysis) {
  if (weActivePron !== 0 || !analysis || !analysis.status || analysis.status === 'consistent') return '';
  const items = weShownReasons(analysis.reasons).map(r => `<li>${weReasonLabels[r] || r}</li>`).join('');
  return `<div class="pg-excluded">${UI.explorerDisplay.excludedLabel}<ul>${items}</ul></div>`;
}
