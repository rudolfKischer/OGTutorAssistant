const WE_DISPLAY_KEY = 'we-display';
const WE_SOUND_JOINER = ' + ';
const GRAPHEME_TOKEN = 'g:';
const PHONEME_TOKEN = 'p:';
let weDisplay = { notation: 'plain', counts: true };
let weSounds = {};
let weDisplayRequested = false;

function weLoadDisplay() {
  weDisplay.notation = UI.explorerDisplay?.defaultNotation || weDisplay.notation;
  try {
    Object.assign(weDisplay, JSON.parse(localStorage.getItem(WE_DISPLAY_KEY) || '{}'));
  } catch (e) {}
  const params = new URLSearchParams(location.search);
  const requested = params.get('notation');
  const lens = params.get('lens');
  if (params.get('syllables') === 'written') weSyllableView = 'written';
  weDisplayRequested = params.get('display') === 'open';
  const selected = params.get('select');
  if (selected) weFeatures = selected.split(',').filter(Boolean);
  if ((UI.explorerDisplay?.lenses || []).some(option => option.id === lens)) weLens = lens;
  if ((UI.explorerDisplay?.notations || []).some(option => option.id === requested)) weDisplay.notation = requested;
}

function weSaveDisplay() {
  try {
    localStorage.setItem(WE_DISPLAY_KEY, JSON.stringify(weDisplay));
  } catch (e) {}
}

function weSoundText(sound) {
  const entry = weSounds[sound];
  return entry ? entry[weDisplay.notation] : sound.replace(/_/g, ' ');
}

function weSoundsText(sounds) {
  if (!sounds.length) return UI.explorerDisplay?.silentLabel || '';
  return sounds.map(weSoundText).join(WE_SOUND_JOINER);
}

function weConceptText(id) {
  const meta = weMeta[id];
  if (!meta) return id;
  if (meta.kind === 'grapheme') return meta.spelling;
  if (meta.kind === 'phoneme') return weSoundsText(meta.sounds);
  if (!WE_PAIR_KINDS.has(meta.kind)) return meta.label;
  return `${meta.spelling} \u2192 ${weSoundsText(meta.sounds)}`;
}

function weRefreshLabels() {
  Object.keys(weMeta).forEach(id => { CONCEPT_LABELS[id] = weConceptText(id); });
}

function weSoundSpansHtml(sounds, interactive = true) {
  if (!sounds.length) return weSoundsText(sounds);
  return sounds.map(sound => {
    if (!interactive) return weSoundText(sound);
    const token = PHONEME_TOKEN + sound;
    const sel = weFeatures.includes(token) ? ' sel' : '';
    return `<span class="pg-s${sel}" data-token="${token}">${weSoundText(sound)}</span>`;
  }).join(WE_SOUND_JOINER);
}

function weGraphemeSpanHtml(spelling, className = 'pg-u-g', interactive = true) {
  if (!interactive) return `<span class="${className}">${spelling}</span>`;
  const token = GRAPHEME_TOKEN + spelling;
  const sel = weFeatures.includes(token) ? ' sel' : '';
  return `<span class="${className}${sel}" data-token="${token}">${spelling}</span>`;
}

function wePillHtml(id, interactive = true) {
  const meta = weMeta[id];
  const dashed = meta?.tail ? ' tail' : '';
  if (meta?.kind === 'grapheme') return `<span class="pg-unit pg-facet g${dashed}"><span class="pg-u-g">${meta.spelling}</span></span>`;
  if (meta?.kind === 'phoneme') return `<span class="pg-unit pg-facet p${dashed}"><span class="pg-u-p big">${weSoundsText(meta.sounds)}</span></span>`;
  if (!meta || !WE_PAIR_KINDS.has(meta.kind)) {
    const label = CONCEPT_LABELS[id] || id.replace(/_/g, ' ');
    return `<span class="pg-unit pg-label" style="background:${conceptColor(id)}"><span class="pg-u-g">${label}</span></span>`;
  }
  const sounds = weSoundSpansHtml(meta.sounds, interactive);
  return `<span class="pg-unit${dashed}">${weGraphemeSpanHtml(meta.spelling, 'pg-u-g', interactive)}<span class="pg-u-p">${sounds}</span></span>`;
}

window.weSetNotation = function(mode) {
  weDisplay.notation = mode;
  weSaveDisplay();
  weRefreshLabels();
  weRerenderDisplay();
};

window.weSetCounts = function(on) {
  weDisplay.counts = on;
  weSaveDisplay();
  weRenderControls();
  weRenderBoard();
};

function weRerenderDisplay() {
  weRenderControls();
  weRenderBoard();
  weRerenderDetail();
}
