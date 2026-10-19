import { blendDetails } from "./blend-selections.js";
import { fill, node } from "./dom.js";

function pairSide(label, value, className) {
  const side = node("div", undefined, className);
  side.append(node("small", label), node("strong", value));
  return side;
}

export function soundPair(target, copy, settings) {
  const card = node("div");
  const mode = settings.notation.currentMode;
  const role = settings.notation.roles[mode];
  const phonemes = target.sounds.map(sound => copy.phonemes[`sound_${sound}`]?.[role] ?? copy.base.phonemeMissing.l);
  const pair = node("div", undefined, `phonogram-pill notation-${mode}`);
  pair.append(pairSide(target.sounds.length > 1 ? copy.pair.sequence.l : copy.pair.sound.l, phonemes.length ? phonemes.join(settings.notation.separator) : copy.base.zero.l, "phoneme-side"),
    pairSide(copy.pair.letters.l, target.spelling, "grapheme-side"));
  card.append(pair);
  const keywords = target.sounds.map(sound => copy.phonemes[`sound_${sound}`]?.n ?? sound);
  card.append(node("small", keywords.join(settings.notation.separator), "sound-keyword"));
  return card;
}

export function targetCard(target, copy, settings) {
  const card = node("div", undefined, "target");
  card.append(soundPair(target, copy, settings));
  const example = settings.examples[target.id];
  if (example) {
    const word = node("p", undefined, "pair-example");
    word.append(node("small", copy.pair.example.l));
    [...example.word].forEach((letter, index) => {
      word.append(node(example.positions.includes(index) ? "mark" : "span", letter));
    });
    card.append(word);
  }
  if (target.status === "not_modeled") card.append(node("p", copy.df.un.m, "pending"));
  const details = node("details", undefined, "pair-id");
  details.append(node("summary", copy.pair.identifier.l), node("code", target.id));
  card.append(details);
  if (target.kind === settings.scope.blendKind) card.append(blendDetails(target, copy));
  return card;
}

function progressCell(mapping, copy) {
  const cell = node("td", undefined, "transfer");
  if (mapping.namespace !== "deployed_catalog_v1") {
    cell.append(node("p", copy.progress.source.m));
    return cell;
  }
  if (!mapping.targets.length) {
    cell.append(node("p", copy.scope.preserve.m));
    return cell;
  }
  const directions = mapping.decoding === mapping.encoding
    ? [[copy.progress.both.l, mapping.decoding]]
    : [[copy.progress.reading.l, mapping.decoding], [copy.progress.spelling.l, mapping.encoding]];
  directions.forEach(([label, transfer]) => {
    cell.append(node("strong", label), node("p", copy.transfers[transfer]?.l ?? transfer));
  });
  return cell;
}

function mappingRow(mapping, copy, settings, inspectWord) {
  const row = node("tr");
  const source = node("td");
  const details = node("details");
  details.append(node("summary", mapping.source_name), node("code", mapping.source_id));
  if (mapping.targets.length) details.append(node("p", mapping.reason));
  details.append(node("code", mapping.source_path));
  source.append(details);
  if (mapping.curriculum) {
    const item = mapping.curriculum;
    source.append(node("small", `${copy.views.row.l} ${item.row} · ${item.group}`));
    source.append(node("code", item.legacy_id ?? copy.views.noid.l));
    if (item.grapheme || item.phoneme) source.append(node("p",
      `${copy.views.original.l}: ${item.grapheme ?? ""} ${item.phoneme ?? ""}`));
  }
  const examples = node("div", undefined, "examples");
  mapping.examples.forEach(word => {
    const button = node("button", word);
    button.addEventListener("click", () => inspectWord(word));
    examples.append(button);
  });
  source.append(examples);
  if (mapping.conflict) source.append(node("p", copy.blend.warning.m, "pending"));
  const targets = node("td");
  const cards = node("div", undefined, "pair-grid");
  mapping.targets.forEach(target => cards.append(targetCard(target, copy, settings)));
  targets.append(mapping.targets.length ? cards : node("strong", mapping.unresolved ? copy.views.pending.m : copy.scope.unchanged.l));
  row.append(source, targets, progressCell(mapping, copy));
  return row;
}

export function renderMappings(mappings, copy, settings, offset, inspectWord) {
  const shown = mappings.slice(offset, offset + settings.pageSize);
  const table = document.querySelector("#mappings");
  table.replaceChildren(...shown.map(mapping => mappingRow(mapping, copy, settings, inspectWord)));
  document.querySelector("#count").textContent = fill(copy.pg.n, {
    shown: mappings.length ? `${offset + 1}–${offset + shown.length}` : 0, total: mappings.length,
  });
  if (!shown.length) {
    const cell = node("td", copy.empty.m);
    cell.colSpan = 3;
    const row = node("tr");
    row.append(cell);
    table.append(row);
  }
  document.querySelector("#previous").disabled = offset === 0;
  document.querySelector("#next").disabled = offset + settings.pageSize >= mappings.length;
}

export function matchingMappings(mappings, state, settings) {
  return mappings.filter(mapping => {
    if (mapping.namespace !== state.namespace) return false;
    if (state.kind === "all" && !mapping.targets.length) return false;
    if (state.kind === "pair" && mapping.targets.length) return false;
    if (state.kind === "pending" && !mapping.targets.some(target => target.status === "not_modeled")) return false;
    const values = [mapping.source_id, mapping.source_name, mapping.curriculum?.group ?? "", ...mapping.targets.flatMap(target =>
      [target.id, target.name, target.spelling, ...target.sounds])];
    return values.join(" ").toLowerCase().includes(state.query.toLowerCase());
  }).sort((first, second) => {
    if (state.view === "curriculum") return first.curriculum.row - second.curriculum.row;
    const rank = value => {
      const index = settings.priorityIds.indexOf(value.source_id);
      return index < 0 ? settings.priorityIds.length : index;
    };
    return rank(first) - rank(second) || first.source_name.localeCompare(second.source_name);
  });
}
