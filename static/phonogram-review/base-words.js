import { fill, node, readJson } from "./dom.js";
import { soundPair } from "./mapping-table.js";

function highlightedWord(word, spans) {
  const line = node("p", undefined, "positioned-word");
  [...word].forEach((letter, index) => {
    line.append(node(spans.some(span => index >= span.start && index < span.end) ? "mark" : "span", letter));
  });
  return line;
}

export async function inspectBaseWord(word, settings, copy, scroll = true) {
  const data = await readJson(settings.routes.baseWord + encodeURIComponent(word));
  const panel = document.querySelector("#base-word-detail");
  panel.dataset.word = word;
  const close = node("button", copy.base.close.a);
  close.onclick = () => { panel.hidden = true; };
  panel.replaceChildren(close, node("h3", data.word), node("strong",
    data.status === settings.base.statuses[0] ? copy.base.consistent.l : copy.base.excludedStatus.l));
  data.reasons.forEach(reason => panel.append(node("p", copy.reasons[reason].l, "pending")));
  panel.append(node("h4", copy.base.syllables.l), node("p", data.syllables.map(syllable => syllable.text).join(" · ")),
    node("h4", copy.base.pronunciation.l), node("code", data.pronunciation.join(" ")));
  Object.values(settings.base.layers).forEach(layer => {
    panel.append(node("h4", layer === settings.base.layers.base ? copy.base.occurrences.l : copy.base.overlays.l));
    const cards = node("div", undefined, "base-grid");
    data.occurrences.filter(occurrence => occurrence.layer === layer).forEach(occurrence => {
      const card = node("div", undefined, "base-card");
      card.append(soundPair(occurrence.pattern, copy, settings), highlightedWord(data.word, occurrence.spans));
      cards.append(card);
    });
    panel.append(cards);
  });
  if (!data.occurrences.length) panel.append(node("p", copy.base.notfound.m));
  const source = node("a", copy.base.sourceData.l);
  source.href = settings.routes.baseWord + encodeURIComponent(word);
  source.target = "_blank";
  panel.append(source);
  panel.hidden = false;
  if (scroll) panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

export function wordList(url, total, settings, copy) {
  const container = node("div", undefined, "base-word-list");
  let offset = 0;
  const load = async () => {
    const data = await readJson(`${url}${url.includes("?") ? "&" : "?"}offset=${offset}&limit=${settings.base.wordPageSize}`);
    const words = node("div", undefined, "word-buttons");
    data.words.forEach(word => {
      const button = node("button", word);
      button.onclick = () => inspectBaseWord(word, settings, copy).catch(fail);
      words.append(button);
    });
    const previous = node("button", copy.base.previous.a);
    const next = node("button", copy.base.next.a);
    previous.disabled = !offset;
    next.disabled = offset + data.words.length >= total;
    previous.onclick = () => { offset -= settings.base.wordPageSize; load().catch(fail); };
    next.onclick = () => { offset += settings.base.wordPageSize; load().catch(fail); };
    container.replaceChildren(words, node("p", data.words.length ? fill(copy.base.page.n, {
      first: offset + 1, last: offset + data.words.length, total,
    }) : copy.base.empty.m), previous, next);
  };
  const fail = () => container.replaceChildren(node("p", copy.base.failure.m, "pending"));
  load().catch(fail);
  return container;
}

export function bindBaseWordNotation(settings, copy) {
  document.addEventListener("notation-change", () => {
    const panel = document.querySelector("#base-word-detail");
    if (!panel.hidden && panel.dataset.word) inspectBaseWord(panel.dataset.word, settings, copy, false)
      .catch(() => panel.append(node("p", copy.base.failure.m)));
  });
}
