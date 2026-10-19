import { attachBlends } from "./scope.js";
import { fill, node } from "./dom.js";
import { targetCard } from "./mapping-table.js";

export function prepareInventories(report, inventories, settings, project) {
  const rows = new Map(inventories.curriculum.map(row => [String(row.row), row]));
  const namespace = settings.views.curriculumNamespace;
  const original = attachBlends(report.mapping.mappings, inventories.blends, settings.scope);
  report.mapping.mappings = project(original, settings.scope).map((mapping, index) => {
    if (mapping.namespace !== namespace) return mapping;
    const curriculum = rows.get(mapping.source_id);
    if (!curriculum) throw new Error(mapping.source_id);
    const unresolved = curriculum.group === settings.views.phonicsGroup
      && original[index].targets.some(target => target.status === "not_modeled");
    const conflict = mapping.targets.some(target => target.kind === settings.scope.blendKind
      && (curriculum.grapheme !== target.spelling || curriculum.legacy_id?.trim() !== target.id));
    return { ...mapping, curriculum, unresolved, conflict,
      targets: curriculum.group === settings.views.phonicsGroup ? mapping.targets : [] };
  });
  report.inventories = { ...inventories, phonograms: [...inventories.phonograms, ...inventories.blends] };
}

export function bindViews(state, settings, render) {
  document.querySelectorAll("[data-view]").forEach(button => {
    button.onclick = () => {
      state.view = button.dataset.view;
      if (state.view !== "base") document.querySelector("#base-word-detail").hidden = true;
      state.namespace = state.view === "curriculum" ? settings.views.curriculumNamespace : settings.defaultNamespace;
      state.kind = state.view === "curriculum" ? "any" : "all";
      state.offset = 0;
      state.query = "";
      ["namespace", "kind", "search"].forEach(id => {
        document.getElementById(id).value = id === "search" ? state.query : state[id];
      });
      render();
    };
  });
}

function renderCatalog(report, state, settings, copy) {
  const curriculum = report.mapping.mappings.filter(row => row.curriculum);
  const targets = report.inventories.phonograms.filter(target =>
    [target.id, target.spelling, ...target.sounds].join(" ").toLowerCase().includes(state.query.toLowerCase()));
  const cards = targets.map(target => {
    const card = targetCard(target, copy, settings);
    const sources = curriculum.filter(row => row.targets.some(pair => pair.id === target.id));
    const note = sources.length ? fill(copy.views.links.n, { count: sources.length }) : copy.views.notlinks.m;
    card.append(node("p", note, "curriculum-links"));
    sources.forEach(source => card.append(node("small", `${source.curriculum.row}: ${source.source_name}`, "sound-keyword")));
    return card;
  });
  const sounds = new Set(report.inventories.phonograms.flatMap(target => target.sounds));
  const summary = node("p", fill(copy.views.sounds.n, { count: sounds.size }), "inventory-sounds");
  document.querySelector("#pair-inventory").replaceChildren(summary, ...cards);
  document.querySelector("#count").textContent = fill(copy.views.count.n, { total: targets.length });
}

export function renderView(report, state, settings, copy) {
  const catalog = state.view === "catalog";
  const base = state.view === "base";
  document.querySelector('[data-copy="sr.x"]').textContent = base ? copy.base.search.l : copy.sr.x;
  document.querySelector("#search").placeholder = base ? copy.base.search.p : copy.sr.p;
  document.querySelector("#view-title").textContent = copy.views[state.view].t;
  document.querySelector("#view-description").textContent = copy.views[state.view].b;
  document.querySelectorAll("[data-view]").forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.view === state.view));
  });
  document.querySelector("#namespace").closest("label").hidden = state.view !== "mapping";
  document.querySelector("#kind").closest("label").hidden = catalog || base;
  document.querySelector("#mapping-table").hidden = catalog || base;
  document.querySelector(".pagination").hidden = catalog || base;
  document.querySelector("#pair-inventory").hidden = !catalog;
  document.querySelector("#base-inventory").hidden = !base;
  document.querySelector(".blend-demo").hidden = base;
  document.querySelector(".scope-note").hidden = base;
  if (catalog) renderCatalog(report, state, settings, copy);
}
