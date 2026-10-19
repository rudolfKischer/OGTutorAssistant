import { bindBaseWordNotation } from "./base-words.js";
import { renderBase } from "./word-base.js";
import { prepareInventories, bindViews, renderView } from "./views.js";
import { bindNotation } from "./notation.js";
import { bindBlendSelections } from "./blend-selections.js";
import { scopedMappings } from "./scope.js";
import { applyCopy, fill, node, readJson } from "./dom.js";
import { matchingMappings, renderMappings } from "./mapping-table.js";

function metrics(report, parity, copy) {
  const values = [
    [report.mapping.source_rows, copy.mt.l], [report.mapping.mappings.filter(row => row.targets.length).length, copy.tg.l],
    [new Set(report.mapping.mappings.flatMap(row => row.targets.map(target => target.id))).size, copy.pp.l],
    [new Set(report.mapping.mappings.flatMap(row => row.targets.filter(target => target.status === "not_modeled").map(target => target.id))).size, copy.un.l],
    [`${report.tags.identical_words.toLocaleString()} / ${report.tags.shared_words.toLocaleString()}`, copy.gd.l],
    [`${parity.results.filter(result => result.matched).length} / ${parity.results.length}`, copy.pa.l],
  ];
  document.querySelector("#metrics").replaceChildren(...values.map(([value, label]) => {
    const card = node("div", undefined, "metric");
    card.append(node("strong", value.toLocaleString()), node("span", label));
    return card;
  }));
}

function regressions(parity, copy) {
  const rows = parity.results.filter(result => result.target).map(result => {
    const row = node("tr");
    const label = allowed => allowed ? copy.rg.allow.l : copy.rg.block.l;
    row.append(node("td", result.name), node("td", label(result.worker), "pending"),
      node("td", label(result.correctedTargetEligible)),
      node("td", result.matched ? copy.rg.pass.l : copy.rg.fail.l, result.matched ? "good" : "pending"));
    return row;
  });
  document.querySelector("#regressions").replaceChildren(...rows);
}

async function inspectWord(word, settings, copy) {
  document.querySelector("#word-input").value = word;
  const data = await readJson(settings.routes.word + encodeURIComponent(word));
  const detail = document.querySelector("#word-detail");
  const alignment = node("div", undefined, "alignment");
  data.alignment.forEach(unit => {
    const card = node("span", unit.grapheme);
    card.append(node("small", unit.sound ?? copy.ar.silent.g));
    alignment.append(card);
  });
  const tags = node("div", undefined, "word-tags");
  data.deployed_tags.forEach(tag => tags.append(node("code", tag)));
  detail.replaceChildren(node("h3", data.word), node("h4", copy.wd.pron.l),
    node("p", data.pronunciation.join(" ")), node("h4", copy.wd.align.l), alignment,
    node("h4", copy.wd.tags.l), tags);
  if (!data.alignment.length && !data.deployed_tags.length) detail.append(node("p", copy.wd.empty.m));
  detail.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function bindMappings(report, settings, copy) {
  const state = { namespace: settings.defaultNamespace, query: "", kind: "all", sight: false, offset: 0, view: settings.views.default };
  state.query = new URLSearchParams(location.search).get(settings.conceptQueryParameter) ?? "";
  if (state.query) state.view = "mapping";
  document.querySelector("#search").value = state.query;
  document.querySelector("#kind").value = state.kind;
  const namespace = document.querySelector("#namespace");
  Object.keys(report.mapping.namespaces).forEach(value => {
    const option = node("option", `${copy.namespaces[value]?.l ?? value} (${report.mapping.namespaces[value]})`);
    option.value = value;
    namespace.append(option);
  });
  namespace.value = state.namespace;
  const inspect = word => inspectWord(word, settings, copy).catch(() => showError(copy));
  const render = () => {
    renderView(report, state, settings, copy);
    if (state.view === "base") renderBase(report.base, state, settings, copy);
    if (["mapping", "curriculum"].includes(state.view)) renderMappings(matchingMappings(report.mapping.mappings, state, settings), copy, settings, state.offset, inspect);
  };
  ["namespace", "kind", "search"].forEach(id => {
    document.getElementById(id).addEventListener(id === "search" ? "input" : "change", event => {
      const key = id === "search" ? "query" : id;
      state[key] = id === "sight" ? event.target.checked : event.target.value;
      state.offset = 0;
      render();
    });
  });
  document.querySelector("#previous").onclick = () => { state.offset -= settings.pageSize; render(); };
  document.querySelector("#next").onclick = () => { state.offset += settings.pageSize; render(); };
  document.querySelector("#word-form").onsubmit = event => {
    event.preventDefault();
    inspect(document.querySelector("#word-input").value.trim().toLowerCase());
  };
  bindViews(state, settings, render);
  bindNotation(settings, copy, render);
  render();
}

function showError(copy) {
  const error = document.querySelector("#error");
  error.textContent = copy.er.m;
  error.hidden = false;
}

async function main() {
  const settings = await readJson("/assets/settings.json");
  const copy = await readJson(settings.routes.copy);
  applyCopy(copy);
  try {
    const [report, parity, inventories, blends, base, review, comparison, checkpoint] = await Promise.all([readJson(settings.routes.report), readJson(settings.routes.parity), readJson(settings.routes.inventories), readJson(settings.routes.blends), readJson(settings.routes.baseSummary), readJson(settings.routes.reviewAudit), readJson(settings.routes.sourceComparison), readJson(settings.routes.checkpoint)]);
    base.checkpoint = checkpoint;
    base.comparison = comparison;
    base.review = review;
    report.base = base;
    inventories.blends = blends.definitions;
    bindBlendSelections(blends, settings, copy);
    bindBaseWordNotation(settings, copy);
    prepareInventories(report, inventories, settings, scopedMappings);
    metrics(report, parity, copy);
    regressions(parity, copy);
    bindMappings(report, settings, copy);
    document.querySelector("#loss").textContent = fill(copy.lv.b, {
      words: report.alignment.strict.words.toLocaleString(), weight: (report.alignment.strict.frequency_share * 100).toFixed(2),
    });
  } catch {
    showError(copy);
  }
}

main();
