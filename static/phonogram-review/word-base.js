import { checkpointSection } from "./checkpoint.js";
import { groupedReview, assessmentDetails, fixesSection, reviewNavigation } from "./review-groups.js";
import { fill, node } from "./dom.js";
import { soundPair } from "./mapping-table.js";
import { wordList } from "./base-words.js";

function patternWords(record, settings, copy) {
  const details = node("details", undefined, "pattern-words");
  details.append(node("summary", copy.base.words.a));
  let loaded = false;
  details.ontoggle = () => {
    if (!details.open || loaded) return;
    loaded = true;
    const select = node("select");
    settings.base.statuses.forEach((status, index) => {
      const option = node("option", index ? copy.base.quarantined.l : copy.base.accepted.l);
      option.value = status;
      select.append(option);
    });
    select.setAttribute("aria-label", copy.base.words.a);
    select.value = record.word_count ? settings.base.statuses[0] : settings.base.statuses[1];
    const list = node("div");
    const render = () => {
      const total = select.value === settings.base.statuses[0] ? record.word_count : record.excluded_words;
      list.replaceChildren(wordList(`${settings.routes.basePattern}${record.pattern.id}/words?status=${select.value}`, total, settings, copy));
    };
    select.onchange = render;
    details.append(select, list);
    render();
  };
  return details;
}

function patternCard(record, settings, copy) {
  const card = node("article", undefined, "base-card");
  card.append(soundPair(record.pattern, copy, settings), node("strong", fill(copy.base.count.n, {
    words: record.word_count.toLocaleString(), occurrences: record.occurrence_count.toLocaleString(),
  })), node("small", fill(copy.base.excluded.n, { count: record.excluded_words.toLocaleString() })));
  if (record.pattern.kind === settings.scope.blendKind) card.append(node("p", copy.base.blend.l));
  const badges = node("div", undefined, "base-badges");
  record.flags.forEach(flag => badges.append(node("span", copy.base[flag].l)));
  card.append(badges, node("p", record.pattern.curriculum.length
    ? fill(copy.base.links.n, { names: record.pattern.curriculum.join(", ") }) : copy.base.nolinks.m));
  record.pattern.definition_ids.forEach(identifier => card.append(node("code", identifier)));
  if (record.review) card.append(assessmentDetails(record.review, copy));
  card.append(patternWords(record, settings, copy));
  return card;
}

function patternSection(section, records, settings, copy, threshold, descriptions = copy.base) {
  const container = node("section", undefined, "base-section");
  container.append(node("h3", descriptions[section].t), node("p", fill(descriptions[section].b, { threshold })),
    node("strong", fill(copy.base.patternTotal.n, { count: records.length })));
  const grid = node("div", undefined, "base-grid");
  let shown = 0;
  const more = node("button", copy.base.more.a);
  const append = () => {
    records.slice(shown, shown + settings.base.sectionPageSize).forEach(record => grid.append(patternCard(record, settings, copy)));
    shown += settings.base.sectionPageSize;
    more.hidden = shown >= records.length;
  };
  more.onclick = append;
  append();
  container.append(grid, more);
  return container;
}

function exclusions(summary, settings, copy) {
  const section = node("section", undefined, "base-section");
  section.append(node("h3", copy.base.source.t), node("p", copy.base.source.b));
  Object.entries(summary.reasons).sort((first, second) => second[1] - first[1]).forEach(([reason, total]) => {
    const details = node("details");
    details.append(node("summary", `${copy.reasons[reason].l} (${total.toLocaleString()})`));
    let loaded = false;
    details.ontoggle = () => {
      if (!details.open || loaded) return;
      loaded = true;
      details.append(wordList(`${settings.routes.baseExcluded}${reason}/words`, total, settings, copy));
    };
    section.append(details);
  });
  return section;
}

export function renderBase(summary, state, settings, copy) {
  if (summary.review.bundle_version !== summary.bundle_version) throw new Error(copy.assessment.mismatch.m);
  const reviews = new Map(summary.review.findings.map(finding => [finding.pattern_id, finding]));
  const records = summary.patterns.map(record => ({ ...record, review: reviews.get(record.pattern.id) })).filter(record => [record.pattern.spelling, ...record.pattern.sounds,
    ...record.pattern.sounds.flatMap(sound => Object.values(copy.phonemes[`sound_${sound}`] ?? {})),
    ...record.pattern.definition_ids, ...record.pattern.curriculum].join(" ").toLowerCase().includes(state.query.toLowerCase()));
  records.sort((first, second) => second.word_count - first.word_count || second.excluded_words - first.excluded_words
    || first.pattern.spelling.localeCompare(second.pattern.spelling));
  document.querySelector("#count").textContent = fill(copy.base.summary.n, {
    included: summary.consistent_words.toLocaleString(), excluded: summary.excluded_words.toLocaleString(), patterns: summary.patterns.length,
  });
  const sections = settings.base.sections.map(section => (section === "teaching"
    ? patternSection(section, records.filter(record => record.section === section), settings, copy, summary.rare_word_threshold)
    : groupedReview(section, records.filter(record => record.section === section), settings, copy, summary.rare_word_threshold, patternSection)));
  document.querySelector("#base-inventory").replaceChildren(checkpointSection(summary, settings, copy), node("p", fill(copy.base.loss.n, {
    weight: (summary.excluded_frequency_share * 100).toFixed(2),
  })), node("p", copy.assessment.b), reviewNavigation(records, settings, copy), ...sections, exclusions(summary, settings, copy), fixesSection(summary, settings, copy));
}
