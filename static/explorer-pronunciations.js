let weActivePron = 0;
let weHeteronymOpen = false;

function wePronCopy() {
  return UI.explorerDisplay.pronunciations;
}

function wePronSoundText(pron) {
  return pron.sounds.map(weSoundText).join(' ');
}

function wePronHint(pron) {
  const sense = pron.senses[0];
  return sense ? (sense.meaning || sense.part_of_speech) : '';
}

function wePronPillHtml(pron) {
  const active = pron.ordinal === weActivePron ? ' active' : '';
  const hint = wePronHint(pron);
  const line = hint ? `<span class="pg-pron-hint">${hint}</span>` : '';
  return `<button class="pg-pron${active}" onclick="weSelectPron(${pron.ordinal})">
    <span class="pg-pron-sounds">${wePronSoundText(pron)}</span>${line}</button>`;
}

function wePronunciationsHtml(w) {
  const items = w.pronunciations || [];
  if (items.length < 2) return '';
  return `<div class="pg-prons">${items.map(wePronPillHtml).join('')}</div>`;
}

function weHeteronymBadgeHtml(w) {
  if (!w.heteronym) return '';
  const copy = wePronCopy();
  const open = weHeteronymOpen ? ' open' : '';
  const possible = w.heteronym.confidence !== 'confirmed';
  const label = possible ? copy.possibleBadge : copy.heteronymBadge;
  const hint = possible ? copy.possibleHint : copy.heteronymHint;
  return `<button class="pg-het${open}${possible ? ' possible' : ''}" title="${hint}" onclick="weToggleHeteronym()">${label}</button>`;
}

function weSenseHtml(sense) {
  const names = wePronCopy().sourceNames;
  const label = [sense.part_of_speech, sense.meaning].filter((part, index, all) => part && all.indexOf(part) === index).join(' — ');
  return `<li><span class="pg-sense-ipa">${sense.ipa}</span> ${label} <span class="pg-sense-src">${names[sense.source] || sense.source}</span></li>`;
}

function weHeteronymDetailsHtml(w) {
  if (!w.heteronym || !weHeteronymOpen) return '';
  const copy = wePronCopy();
  const senses = w.heteronym.senses.length
    ? `<div class="pg-het-title">${copy.sensesTitle}</div><ul class="pg-senses">${w.heteronym.senses.map(weSenseHtml).join('')}</ul>` : '';
  const possible = w.heteronym.confidence !== 'confirmed';
  const only = !possible && (w.pronunciations || []).length < 2 ? `<div class="pg-pron-note">${copy.onlyOne}</div>` : '';
  const listed = possible ? `<div class="pg-pron-note">${copy.listedNote}</div>` : '';
  const names = w.heteronym.sources.map(source => copy.sourceNames[source] || source).join(', ');
  return `<div class="pg-het-details">${senses}${only}${listed}
    <div class="pg-het-meta">${copy.sourcesTitle}: ${names} · <a href="${w.heteronym.link}" target="_blank" rel="noopener">${copy.wiktionaryLink}</a></div>
    <div class="pg-het-meta">${copy.attribution}</div></div>`;
}

function weActiveAnalysis(w) {
  const items = w.pronunciations || [];
  const active = items.find(item => item.ordinal === weActivePron);
  if (!active || active.ordinal === 0) return { analysis: w.phonogram_analysis, main: true };
  return { analysis: active.analysis, main: false };
}

window.weSelectPron = function(ordinal) {
  weActivePron = ordinal;
  weRerenderDetail();
};

window.weToggleHeteronym = function() {
  weHeteronymOpen = !weHeteronymOpen;
  weRerenderDetail();
};

function weResetPronunciation(word) {
  if (weDetailWord === word) return;
  weActivePron = 0;
  weHeteronymOpen = false;
}
