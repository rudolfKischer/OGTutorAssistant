const WE_COUNT_MS = 260;
let weBaseline = null;
let weLastPreview = null;
let weAnimations = new WeakMap();

function weEase(progress) {
  return 1 - Math.pow(1 - progress, 3);
}

function weAnimateNumber(element, target, format) {
  const from = element.dataset.value === undefined ? target : Number(element.dataset.value);
  element.dataset.value = target;
  cancelAnimationFrame(weAnimations.get(element));
  const start = performance.now();
  const step = now => {
    const progress = Math.min((now - start) / WE_COUNT_MS, 1);
    element.textContent = format(from + (target - from) * weEase(progress));
    if (progress < 1) weAnimations.set(element, requestAnimationFrame(step));
  };
  weAnimations.set(element, requestAnimationFrame(step));
}

const weWhole = value => Math.round(value).toLocaleString();
const wePercent = value => `${value.toFixed(1)}%`;

function weStatTileHtml(stat) {
  return `<div class="pg-set-stat" data-tip="${stat.hint}"><strong data-stat="${stat.id}">–</strong><em data-sub="${stat.id}"> </em><span>${stat.label}</span></div>`;
}

function weSwitchHtml(category) {
  const copy = weSettingsCopy();
  return `<div class="pg-switch-wrap"><span class="pg-switch-text" data-switch-text="${category.id}"></span>
    <button type="button" class="pg-switch" role="switch" data-switch="${category.id}" data-tip="${category.hint}" aria-label="${category.label}"><span></span></button></div>`;
}

function wePillControlHtml(category) {
  const columns = weSettingsCopy().grid.columns;
  const buttons = columns.map(column => `<button type="button" class="pg-pill-cell" data-category="${category.id}" data-mode="${column.id}" data-tip="${column.hint}" aria-label="${column.label}"></button>`).join('');
  return `<div class="pg-pill" data-pill="${category.id}"><span class="pg-pill-thumb"></span>${buttons}</div>`;
}

function weCategoryRowHtml(category) {
  const control = category.toggle ? weSwitchHtml(category) : wePillControlHtml(category);
  return `<div class="pg-set-grid-row"><span class="pg-set-name" data-tip="${category.hint}">${category.label}<i>i</i></span>
    <span class="pg-set-kept" data-kept="${category.id}" data-tip="${weSettingsCopy().grid.countHint}">\u00a0</span>${control}</div>`;
}

function weGridHtml() {
  const grid = weSettingsCopy().grid;
  const heads = grid.columns.map(column => `<span data-tip="${column.hint}">${column.label}</span>`).join('');
  return `<div class="pg-set-grid"><div class="pg-set-grid-head"><span>${grid.title}</span><span data-tip="${grid.countHint}">${grid.countLabel}</span><span class="pg-set-heads">${heads}</span></div>
    ${weSettingsCopy().categories.map(weCategoryRowHtml).join('')}</div>`;
}

function weStatsHtml() {
  return `<div class="pg-set-stats">${weSettingsCopy().stats.map(weStatTileHtml).join('')}</div>`;
}

function weSyncModes(panel) {
  const order = weSettingsCopy().grid.columns.map(column => column.id);
  panel.querySelectorAll('[data-pill]').forEach(pill => {
    const index = order.indexOf(weDraft.modes[pill.dataset.pill]);
    pill.style.setProperty('--index', index);
    pill.dataset.mode = order[index];
  });
  const labels = weSettingsCopy().toggleLabels;
  panel.querySelectorAll('[data-switch]').forEach(button => {
    const on = weDraft.modes[button.dataset.switch] === 'remove';
    button.setAttribute('aria-checked', on);
    panel.querySelector(`[data-switch-text="${button.dataset.switch}"]`).textContent = on ? labels.on : labels.off;
  });
}

function weSetSub(panel, id, text) {
  panel.querySelector(`[data-sub="${id}"]`).textContent = text;
}

function weRenderPreview(data) {
  const panel = document.getElementById('we-settings');
  if (!panel || panel.hidden) return;
  const base = weBaseline || data;
  const stat = id => panel.querySelector(`[data-stat="${id}"]`);
  weAnimateNumber(stat('words'), data.words, weWhole);
  weAnimateNumber(stat('usage'), data.usage_share * 100, wePercent);
  weAnimateNumber(stat('phonograms'), data.phonograms, weWhole);
  weAnimateNumber(stat('rare'), data.rare_phonograms, weWhole);
  const subs = { words: base.total_words, phonograms: base.phonograms, rare: base.rare_phonograms };
  weSettingsCopy().stats.forEach(item => weSetSub(panel, item.id, item.sub.replace('{total}', (subs[item.id] ?? 0).toLocaleString())));
  weSettingsCopy().categories.forEach(category => {
    const group = data.groups[category.id];
    const element = panel.querySelector(`[data-kept="${category.id}"]`);
    element.classList.toggle('muted', group.kept === group.total);
    element.textContent = `${group.kept.toLocaleString()} / ${group.total.toLocaleString()}`;
  });
}

function weSettingsGroups() {
  return JSON.stringify(Object.fromEntries(weSettingsCopy().categories.map(category => [category.id, category.flags])));
}

async function weFetchPreview(state) {
  const params = new URLSearchParams({ groups: weSettingsGroups() });
  if (weSettingsStateActive(state)) params.set('policy', weSettingsPolicy(state));
  return (await fetch(`/api/policy-preview?${params}`)).json();
}

async function weSettingsRefreshPreview() {
  if (!weBaseline) weBaseline = await weFetchPreview(weSettingsPreset('everything'));
  const request = JSON.stringify(weDraft);
  const data = await weFetchPreview(weDraft);
  if (request === JSON.stringify(weDraft)) weRenderPreview(data);
}

const WE_TIP_DELAY = 140;
const WE_TIP_GAP = 10;
let weTipTimer = null;

function weTipElement() {
  let tip = document.getElementById('we-tip');
  if (!tip) {
    document.body.insertAdjacentHTML('beforeend', '<div id="we-tip" class="pg-tip"></div>');
    tip = document.getElementById('we-tip');
  }
  return tip;
}

function weShowTip(target) {
  const tip = weTipElement();
  tip.textContent = target.dataset.tip;
  tip.classList.add('show');
  const box = target.getBoundingClientRect();
  const width = tip.offsetWidth;
  const left = Math.min(Math.max(8, box.left + box.width / 2 - width / 2), window.innerWidth - width - 8);
  const above = box.top - tip.offsetHeight - WE_TIP_GAP;
  tip.style.left = `${left}px`;
  tip.style.top = `${above > 8 ? above : box.bottom + WE_TIP_GAP}px`;
}

function weHideTip() {
  clearTimeout(weTipTimer);
  weTipElement().classList.remove('show');
}

function weBindTips(panel) {
  panel.addEventListener('mouseover', event => {
    const target = event.target.closest('[data-tip]');
    if (!target || !panel.contains(target)) return;
    clearTimeout(weTipTimer);
    weTipTimer = setTimeout(() => weShowTip(target), WE_TIP_DELAY);
  });
  panel.addEventListener('mouseout', event => { if (event.target.closest('[data-tip]')) weHideTip(); });
  panel.addEventListener('mousedown', weHideTip);
}
