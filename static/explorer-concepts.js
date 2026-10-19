let weMeta = {};
let weDynamicFamilies = [];
let weReasonLabels = {};
let weRedundantReasons = {};
let weDetailWord = null;
let weLens = 'phonograms';
const WE_PAIR_KINDS = new Set(['phonogram', 'blend', 'unmodeled']);
const WE_FACET_KINDS = new Set(['grapheme', 'phoneme']);
const WE_EVIDENCE_KINDS = new Set(['phonogram', 'unmodeled', 'unresolved']);

async function weLoadConceptMeta() {
  const res = await fetch('/api/concept-catalog');
  if (!res.ok) return;
  const data = await res.json();
  weReasonLabels = data.reason_labels || {};
  weRedundantReasons = data.redundant_reasons || {};
  weSounds = data.sounds || {};
  weMeta = {};
  data.concepts.forEach(row => { weMeta[row.concept] = row; });
  weDynamicFamilies = data.families.map(fam => ({
    ...fam,
    ids: data.concepts.filter(row => row.family === fam.id)
      .sort((a, b) => a.sort_key.localeCompare(b.sort_key)).map(row => row.concept),
  }));
  weRefreshLabels();
}

function weBaseFamilies() {
  const reworked = weDynamicFamilies.length && UI.conceptFamiliesReworked;
  return reworked ? UI.conceptFamiliesReworked : (UI.conceptFamilies || []);
}

function weAllFamilies(allLenses = false) {
  const order = UI.groupOrder || [];
  const dynamic = weDynamicFamilies.filter(fam => allLenses || fam.lens === weLens);
  const rank = fam => { const i = order.indexOf(fam.group); return i < 0 ? order.length : i; };
  return [...dynamic, ...weBaseFamilies()]
    .map((fam, index) => ({ fam, index }))
    .sort((a, b) => rank(a.fam) - rank(b.fam) || a.index - b.index)
    .map(item => item.fam);
}

function weFamilyIds(fam) {
  if (fam.ids) return fam.ids;
  let ids;
  if (fam.filter) ids = fam.filter.map(f => fam.prefix + f);
  else if (fam.prefixes) ids = Object.keys(weCatalog).filter(k => fam.prefixes.some(p => k.startsWith(p))).sort();
  else if (Array.isArray(fam.prefix)) ids = fam.prefix;
  else ids = Object.keys(weCatalog).filter(k => k.startsWith(fam.prefix)).sort();
  if (fam.exclude) {
    const excluded = new Set(fam.exclude.map(f => fam.prefix + f));
    ids = ids.filter(id => !excluded.has(id));
  }
  return ids.filter(id => !weMeta[id]?.family);
}

function weConceptPresent(id) {
  if (!(weCatalog[id] > 0)) return false;
  const present = weDynamicCounts?.present;
  if (!weSettingsActive() || !present) return true;
  return weFeatures.includes(id) || weDynamicPresent.has(id);
}

function weVisibleFamilies(allLenses = false) {
  const entries = weAllFamilies(allLenses).map(fam => ({ fam, ids: weFamilyIds(fam).filter(weConceptPresent) }));
  const claimed = new Set(entries.flatMap(entry => entry.ids));
  const rest = Object.keys(weCatalog).filter(id => weConceptPresent(id) && !claimed.has(id)).sort();
  const other = UI.explorerDisplay?.otherFamily;
  if (rest.length && other) entries.push({ fam: { ...other }, ids: rest });
  return entries.filter(entry => entry.ids.length);
}

function weKindColor(concept) {
  const kind = weMeta[concept]?.kind;
  return kind ? UI.concepts?.kindColors?.[kind] : undefined;
}

function weIsPhonogramConcept(concept) {
  return WE_EVIDENCE_KINDS.has(weMeta[concept]?.kind);
}
