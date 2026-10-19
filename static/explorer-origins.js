function weOriginBadgesHtml(w) {
  const copy = UI.explorerDisplay.origins;
  const flags = w.origins || {};
  return copy.order.filter(key => flags[key] !== undefined).map(key => {
    const detail = weOriginDetail(copy, key, flags[key]);
    const hint = key === 'unusual_spelling' && flags[key] ? `${copy.hints[key]}: ${flags[key]}` : copy.hints[key];
    return `<span class="pg-origin ${key}" title="${hint}">${copy.labels[key]}${detail}</span>`;
  }).join('');
}

function weOriginDetail(copy, key, value) {
  if (copy.quietDetails.includes(key) || !value) return '';
  const parts = String(value).split(', ').map(item => copy.details[item] ?? item).filter(Boolean);
  const unique = [...new Set(parts)].slice(0, copy.detailLimit);
  return unique.length ? ` \u00b7 ${unique.join(', ')}` : '';
}

const weOriginSelected = new Set();
let weOriginWithout = false;
let weOriginOpen = false;

function weOriginFilterValue() {
  const prefix = weOriginWithout ? 'not_' : '';
  return [...weOriginSelected].map(flag => prefix + flag).join(',');
}

function weOriginMode() {
  return weOriginWithout ? '' : 'any';
}

function weOriginChipHtml(copy, key) {
  const on = weOriginSelected.has(key) ? ' on' : '';
  return `<button type="button" class="pg-tag${on}" data-flag="${key}" data-tip="${copy.hints[key] || ''}">${copy.labels[key]}</button>`;
}

function weOriginModeHtml(copy) {
  const buttons = [[false, copy.withLabel], [true, copy.withoutLabel]].map(([without, label]) =>
    `<button type="button" class="pg-seg${weOriginWithout === without ? ' active' : ''}" data-without="${without}">${label}</button>`).join('');
  return `<span class="pg-segs">${buttons}</span>`;
}

function weOriginHeaderHtml(copy) {
  const count = weOriginSelected.size;
  const badge = count ? ` (${count})` : '';
  return `<div class="pg-tags-toggle" id="we-origin-toggle">${weOriginOpen ? '\u25be' : '\u25b8'} ${copy.filterLabel}${badge}</div>`;
}

function weRenderOriginFilter() {
  const wrap = document.getElementById('we-rf-origin-wrap');
  const copy = UI.explorerDisplay?.origins;
  if (!wrap || !copy || !weDynamicFamilies.length) return;
  wrap.hidden = false;
  const chips = copy.filterOrder.map(key => weOriginChipHtml(copy, key)).join('');
  const body = weOriginOpen ? `<div class="pg-tags">${weOriginModeHtml(copy)}${chips}</div>` : '';
  wrap.innerHTML = weOriginHeaderHtml(copy) + body;
  wrap.querySelector('#we-origin-toggle').addEventListener('click', () => { weOriginOpen = !weOriginOpen; weRenderOriginFilter(); });
  wrap.querySelectorAll('.pg-tag').forEach(chip => chip.addEventListener('click', () => weToggleOriginTag(chip.dataset.flag)));
  wrap.querySelectorAll('[data-without]').forEach(button => button.addEventListener('click', () => {
    weOriginWithout = button.dataset.without === 'true';
    weRefreshOrigins();
  }));
}

function weToggleOriginTag(flag) {
  if (weOriginSelected.has(flag)) weOriginSelected.delete(flag); else weOriginSelected.add(flag);
  weRefreshOrigins();
}

function weRefreshOrigins() {
  weRenderOriginFilter();
  weOffset = 0;
  weSearch();
  weFetchBrowseCounts();
}
