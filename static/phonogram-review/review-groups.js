import { fill, node } from "./dom.js";

export function reviewGroupFor(record, settings) {
  const facts = {
    section: record.section, defined: Boolean(record.pattern.definition_ids.length),
    observed: record.word_count > 0, excluded: record.excluded_words > 0,
    rare: record.flags.includes("rare"), punctuation: /[^a-z_]/.test(record.pattern.spelling),
  };
  const group = settings.base.reviewGroups.find(rule =>
    Object.entries(rule.conditions).every(([key, expected]) => facts[key] === expected));
  return group?.id;
}

export function groupedReview(section, records, settings, copy, threshold, renderSection) {
  const container = node("section", undefined, "base-section");
  container.append(node("h3", copy.base[section].t), node("p", copy.base[section].b));
  settings.base.reviewGroups.filter(group => group.conditions.section === section).forEach(group => {
    const matches = records.filter(record => reviewGroupFor(record, settings) === group.id);
    const details = node("details", undefined, "review-group");
    details.id = `review-group-${group.id}`;
    details.append(node("summary", `${copy.reviewGroups[group.id].t} (${matches.length})`));
    let rendered = false;
    details.ontoggle = () => {
      if (!details.open || rendered) return;
      rendered = true;
      details.append(renderSection(group.id, matches, settings, copy, threshold, copy.reviewGroups));
    };
    if (matches.length && document.querySelector("#search").value) details.open = true;
    container.append(details);
  });
  return container;
}

export function assessmentDetails(review, copy) {
  const details = node("details", undefined, "assessment-details");
  const assessment = review.assessment;
  details.append(node("summary", copy.assessments[assessment.category].l),
    node("strong", assessment.status === "Verified" ? copy.assessment.verified.l : copy.assessment.unverified.l),
    node("p", assessment.note), node("p", `${copy.assessment.fixes.l}: ${assessment.fix_ids.join(", ")}`));
  [[copy.assessment.examples.l, review.consistent_examples], [copy.assessment.excluded.l, review.excluded_examples]]
    .forEach(([label, examples]) => details.append(node("p", `${label}: ${examples.join(", ") || copy.assessment.none.l}`)));
  return details;
}

export function fixesSection(summary, settings, copy) {
  const section = node("section", undefined, "base-section");
  section.id = "base-fixes";
  section.append(node("h3", copy.fixes.t), node("p", copy.fixes.b));
  settings.base.fixIds.forEach(identifier => {
    const details = node("details");
    details.id = identifier;
    details.append(node("summary", copy.fixes[identifier].t), node("p", copy.fixes[identifier].b));
    section.append(details);
  });
  if (summary.comparison.bundle_version === summary.bundle_version) {
    const counts = summary.comparison.counts;
    section.append(node("p", fill(copy.comparison.n, {
      variants: counts.matches_other_cmu_variant.toLocaleString(),
      syllables: counts.syllabified_matches_selected.toLocaleString(),
    })));
  }
  Object.entries(settings.base.datasetSources).forEach(([key, url]) => {
    const details = node("details");
    const link = node("a", copy.datasets[key].a);
    link.href = url;
    link.target = "_blank";
    link.rel = "noreferrer";
    details.append(node("summary", copy.datasets[key].t), node("p", copy.datasets[key].b), link);
    section.append(details);
  });
  const download = node("a", copy.assessment.download.a);
  download.href = settings.routes.reviewAudit;
  download.download = "phonogram-review-audit.json";
  section.append(download);
  return section;
}

export function reviewNavigation(records, settings, copy) {
  const nav = node("nav", undefined, "review-navigation");
  nav.setAttribute("aria-label", copy.assessment.t);
  settings.base.reviewGroups.forEach(group => {
    const count = records.filter(record => reviewGroupFor(record, settings) === group.id).length;
    const link = node("a", `${copy.reviewGroups[group.id].t} (${count})`);
    link.href = `#review-group-${group.id}`;
    link.onclick = () => { document.getElementById(`review-group-${group.id}`).open = true; };
    nav.append(link);
  });
  const fixes = node("a", copy.fixes.a);
  fixes.href = "#base-fixes";
  nav.append(fixes);
  return nav;
}
