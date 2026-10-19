import { fill, node } from "./dom.js";
import { soundPair } from "./mapping-table.js";
import { inspectBaseWord } from "./base-words.js";

function checkpointCard(row, settings, copy) {
  const card = node("article", undefined, "base-card");
  card.append(soundPair(row.pattern, copy, settings),
    node("p", `${copy.checkpoint.before.l}: ${row.before} → ${copy.checkpoint.after.l}: ${row.after}`),
    node("small", `${copy.checkpoint.excluded.l}: ${row.excluded_before} → ${row.excluded_after}`));
  row.examples.forEach(word => {
    const button = node("button", word);
    button.onclick = () => inspectBaseWord(word, settings, copy)
      .catch(() => card.append(node("p", copy.base.failure.m)));
    card.append(button);
  });
  return card;
}

function statusChanges(data, settings, copy) {
  const details = node("details");
  details.append(node("summary", copy.checkpoint.boundaries.t), node("p", copy.checkpoint.boundaries.b));
  data.status_changes.forEach(change => {
    const button = node("button", change.word);
    button.onclick = () => inspectBaseWord(change.word, settings, copy)
      .catch(() => details.append(node("p", copy.base.failure.m)));
    details.append(button);
  });
  return details;
}

export function checkpointSection(summary, settings, copy) {
  const data = summary.checkpoint;
  if (data.bundle_version !== summary.bundle_version) throw new Error(copy.checkpoint.failure.m);
  const section = node("section", undefined, "base-section");
  section.id = "fix-01-checkpoint";
  section.append(node("h3", copy.checkpoint.t), node("p", copy.checkpoint.b),
    node("strong", fill(copy.checkpoint.summary.n, Object.fromEntries(
      Object.entries(data.counts).map(([key, value]) => [key, value.toLocaleString()])))));
  const grid = node("div", undefined, "base-grid");
  data.pairs.forEach(row => grid.append(checkpointCard(row, settings, copy)));
  const download = node("a", copy.checkpoint.download.a);
  download.href = settings.routes.checkpoint;
  download.download = "fix-01.json";
  section.append(grid, statusChanges(data, settings, copy), download);
  return section;
}
