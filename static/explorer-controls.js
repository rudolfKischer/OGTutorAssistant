let weDisplayOpen = false;
let weDetailData = null;
const WE_ICON = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M2 4h7M13 4h1M2 8h2M8 8h6M2 12h8M13 12h1"/><circle cx="11" cy="4" r="1.6"/><circle cx="6" cy="8" r="1.6"/><circle cx="11.5" cy="12" r="1.6"/></svg>';

function weSegmentsHtml(options, active, handler) {
  const buttons = options.map(option =>
    `<button class="pg-seg${option.id === active ? ' active' : ''}" title="${option.hint || ''}" onclick="${handler}('${option.id}')">${option.label}</button>`).join('');
  return `<div class="pg-segs block">${buttons}</div>`;
}

function weNotationOptionsHtml(copy) {
  return copy.notations.map(option => {
    const sample = weSounds[copy.sampleSound]?.[option.id] || '';
    const active = option.id === weDisplay.notation ? ' active' : '';
    return `<button class="pg-opt${active}" onclick="weSetNotation('${option.id}')"><span>${option.label}</span><span class="pg-opt-sample">${sample}</span></button>`;
  }).join('');
}

function weDisplayPopoverHtml(copy) {
  const checked = weDisplay.counts ? ' checked' : '';
  return `<div class="pg-pop"><div class="pg-pop-title">${copy.notationTitle}</div>${weNotationOptionsHtml(copy)}
    <div class="pg-pop-sep"></div>
    <label class="pg-pop-row"><span>${copy.countsTitle}</span><input type="checkbox"${checked} onchange="weSetCounts(this.checked)"></label></div>`;
}

function weRenderDisplay() {
  const el = document.getElementById('we-display');
  const copy = UI.explorerDisplay;
  if (!el || !copy) return;
  const open = weDisplayOpen ? ' open' : '';
  el.innerHTML = `<button class="pg-icon-btn${open}" title="${copy.displayHint}" onclick="weToggleDisplay(event)">${WE_ICON}</button>${weDisplayOpen ? weDisplayPopoverHtml(copy) : ''}`;
}

function weRenderControls() {
  const el = document.getElementById('we-controls');
  const copy = UI.explorerDisplay;
  if (!el || !copy) return;
  el.innerHTML = weSegmentsHtml(copy.lenses, weLens, 'weSetLens') + weSegmentsHtml(copy.modes, weMode, 'weSetMode');
  weRenderDisplay();
}

function weChipHtml(id) {
  const copy = UI.explorerDisplay;
  return `<button class="pg-chip" data-remove="${id}" title="${copy.removeHint}">${wePillHtml(id, false)}<span class="pg-chip-x">&times;</span></button>`;
}

function weRenderTray() {
  const el = document.getElementById('we-selection');
  const copy = UI.explorerDisplay;
  if (!el || !copy) return;
  el.hidden = false;
  const count = weFeatures.length;
  const body = count ? weFeatures.map(weChipHtml).join('') : `<span class="pg-sel-empty">${copy.emptySelection}</span>`;
  el.innerHTML = `<div class="pg-sel-head"><span class="pg-sel-label">${copy.selectedLabel}${count ? ' \u00b7 ' + count : ''}</span>
    <button class="pg-sel-clear" id="we-clear" title="${copy.clearHint}" onclick="weClearAll()"${count ? '' : ' style="visibility:hidden"'}>${copy.clearLabel}</button></div>
    <div class="pg-chips">${body}</div>`;
}

function weRerenderDetail() {
  const panel = document.getElementById('we-detail-panel');
  if (!weDetailWord || !weDetailData || !panel) return;
  const scroll = panel.scrollTop;
  weRenderDetail(weDetailData);
  panel.scrollTop = scroll;
}

function weRenderSelection() {
  weRenderTray();
  weRerenderDetail();
}

window.weToggleDisplay = function(event) {
  event.stopPropagation();
  weDisplayOpen = !weDisplayOpen;
  weRenderDisplay();
};

document.addEventListener('click', event => {
  const chip = event.target.closest('[data-remove]');
  if (chip) weToggleFeature(chip.dataset.remove);
});

document.addEventListener('click', event => {
  if (!weDisplayOpen || event.target.closest('#we-display')) return;
  weDisplayOpen = false;
  weRenderDisplay();
});

window.weSetLens = function(lens) {
  weLens = lens;
  weRenderControls();
  weRenderBoard();
};
