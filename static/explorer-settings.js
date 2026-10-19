const WE_SETTINGS_KEY = 'we-word-settings';
const WE_SETTINGS_DELAY = 250;
let weSettings = null;
let weDraft = null;
let weSettingsTimer = null;
let weDownOnOverlay = false;

function weSettingsCopy() {
  return UI.explorerDisplay.settings;
}

function weClone(state) {
  return JSON.parse(JSON.stringify(state));
}

function weSettingsPreset(id) {
  return weClone(weSettingsCopy().presets.find(item => item.id === id).state);
}

function weSettingsLoad() {
  try {
    const saved = JSON.parse(localStorage.getItem(WE_SETTINGS_KEY));
    if (saved && saved.modes) return saved;
  } catch (error) {
    return weSettingsPreset('everything');
  }
  return weSettingsPreset('everything');
}

function weSettingsStateActive(state) {
  return Boolean(state.keepTop || state.maxRank || state.rare || Object.values(state.modes).some(mode => mode !== 'keep'));
}

function weSettingsActive() {
  return weSettingsStateActive(weSettings);
}

function weSettingsPolicy(state = weSettings) {
  const limits = {};
  weSettingsCopy().categories.forEach(category => {
    const mode = state.modes[category.id];
    if (mode === 'keep') return;
    category.flags.forEach(flag => { limits[flag] = mode === 'remove' ? 0 : state.commonRank; });
  });
  return JSON.stringify({ keep_top: state.keepTop, max_rank: state.maxRank, rare: state.rare, limits });
}

function weSettingsParam(params) {
  if (weSettingsActive()) params.set('policy', weSettingsPolicy());
}

function weSettingsChanged() {
  return JSON.stringify(weDraft) !== JSON.stringify(weSettings);
}

function weSettingsPresetsHtml() {
  const buttons = weSettingsCopy().presets.map(item => `<button type="button" class="pg-seg" data-preset="${item.id}" data-tip="${item.hint}">${item.label}</button>`).join('');
  return `<div class="pg-set-presets"><span class="pg-segs">${buttons}</span></div>`;
}

function weSettingsSyncFooter() {
  const changed = weSettingsChanged();
  document.getElementById('we-settings-save').disabled = !changed;
  document.getElementById('we-settings-unsaved').textContent = changed ? weSettingsCopy().unsaved : '\u00a0';
  document.querySelectorAll('[data-preset]').forEach(button => {
    button.classList.toggle('active', JSON.stringify(weSettingsPreset(button.dataset.preset)) === JSON.stringify(weDraft));
  });
}

function weSettingsEdited() {
  weSettingsSyncFooter();
  weSettingsRefreshPreview();
}

function weSettingsSyncAll(panel) {
  weSyncModes(panel);
  weSyncSliders(panel);
  weSettingsEdited();
}

function weSettingsBodyHtml() {
  const copy = weSettingsCopy();
  const sliders = ['commonRank', 'keepTop', 'maxRank', 'rare'].map(weSliderRowHtml).join('');
  return `${weStatsHtml()}${weSettingsPresetsHtml()}${weGridHtml()}<div class="pg-set-section" data-tip="${copy.frequencyHint}">${copy.limitsTitle}</div>${sliders}`;
}

function weSettingsRenderPanel() {
  const copy = weSettingsCopy();
  const panel = document.getElementById('we-settings');
  panel.innerHTML = `<div class="pg-set-card"><div class="pg-set-head"><h3>${copy.title}</h3><p>${copy.subtitle}</p></div>
    <div class="pg-set-body">${weSettingsBodyHtml()}</div>
    <div class="pg-set-foot"><button type="button" class="pg-set-link" id="we-settings-reset">${copy.reset}</button><span class="pg-set-unsaved" id="we-settings-unsaved">\u00a0</span>
    <button type="button" class="pg-set-ghost" id="we-settings-cancel">${copy.cancel}</button><button type="button" class="pg-set-primary" id="we-settings-save">${copy.save}</button></div></div>`;
  weBindSettingsPanel(panel);
  weSettingsSyncAll(panel);
}


function weBindSettingsPanel(panel) {
  panel.querySelector('#we-settings-cancel').addEventListener('click', weSettingsClose);
  panel.querySelector('#we-settings-save').addEventListener('click', weSettingsCommit);
  panel.querySelector('#we-settings-reset').addEventListener('click', () => { weDraft = weSettingsPreset('everything'); weSettingsSyncAll(panel); });
  panel.querySelectorAll('[data-preset]').forEach(item => item.addEventListener('click', () => { weDraft = weSettingsPreset(item.dataset.preset); weSettingsSyncAll(panel); }));
  panel.querySelectorAll('[data-mode]').forEach(item => item.addEventListener('click', () => {
    weDraft.modes[item.dataset.category] = item.dataset.mode;
    weSyncModes(panel);
    weSettingsEdited();
  }));
  panel.querySelectorAll('[data-switch]').forEach(button => button.addEventListener('click', () => {
    weDraft.modes[button.dataset.switch] = button.getAttribute('aria-checked') === 'true' ? 'keep' : 'remove';
    weSyncModes(panel);
    weSettingsEdited();
  }));
  weBindSliders(panel, (id, value) => { weDraft[id] = value; weSettingsEdited(); });
}

function weSettingsCommit() {
  weSettings = weClone(weDraft);
  try { localStorage.setItem(WE_SETTINGS_KEY, JSON.stringify(weSettings)); } catch (error) { weSettingsRenderButton(); }
  weSettingsRenderButton();
  weSettingsClose();
  clearTimeout(weSettingsTimer);
  weSettingsTimer = setTimeout(() => { weOffset = 0; weSearch(); weFetchBrowseCounts(); if (weDetailWord) weOpenDetail(weDetailWord); }, WE_SETTINGS_DELAY);
}

function weSettingsClose() {
  weHideTip();
  document.getElementById('we-settings').hidden = true;
}

function weSettingsOpen() {
  const preset = new URLSearchParams(location.search).get('draft');
  weDraft = preset && weSettingsCopy().presets.some(item => item.id === preset) ? weSettingsPreset(preset) : weClone(weSettings);
  document.getElementById('we-settings').hidden = false;
  weSettingsRenderPanel();
}

function weSettingsToggle() {
  if (document.getElementById('we-settings').hidden) weSettingsOpen(); else weSettingsClose();
}

function weSettingsRenderButton() {
  document.getElementById('we-settings-button').classList.toggle('active', weSettingsActive());
}

function weSettingsInit() {
  weSettings = weSettingsLoad();
  document.querySelector('header').insertAdjacentHTML('beforeend', `<button type="button" id="we-settings-button" class="pg-set-button">${weSettingsCopy().button}</button>`);
  document.body.insertAdjacentHTML('beforeend', '<div id="we-settings" class="pg-set-overlay" hidden></div>');
  const overlay = document.getElementById('we-settings');
  document.getElementById('we-settings-button').addEventListener('click', weSettingsToggle);
  weBindTips(overlay);
  overlay.addEventListener('mousedown', event => { weDownOnOverlay = event.target === overlay; });
  overlay.addEventListener('click', event => { if (event.target === overlay && weDownOnOverlay) weSettingsClose(); });
  weSettingsRenderButton();
  if (new URLSearchParams(location.search).get('settings') === 'open') weSettingsOpen();
}
