import { fill, node } from "./dom.js";

export function blendDetails(target, copy) {
  const details = node("details", undefined, "blend-details");
  details.append(node("summary", copy.blend.mapping.l), node("strong", copy.blend[target.context].l),
    node("code", target.id), node("p", copy.blend.components.l));
  target.components.forEach(component => details.append(node("code",
    `${component.phonogram_id} [${component.start}, ${component.end})`)));
  ["reading", "spelling"].forEach(direction => {
    const button = node("button", copy.blend[direction].a);
    button.type = "button";
    button.onclick = () => document.dispatchEvent(new CustomEvent("blend-select", {
      detail: { direction, concept_id: target.id },
    }));
    details.append(button);
  });
  return details;
}

function renderSelections(selections, copy) {
  const rows = selections.map(selection => node("p", fill(copy.blend.saved.n, {
    direction: copy.progress[selection.direction].l,
    concept: selection.concept_id, version: selection.bundle_version,
  })));
  document.querySelector("#blend-selections").replaceChildren(
    ...(rows.length ? rows : [node("p", copy.blend.empty.m)]));
}

export function bindBlendSelections(data, settings, copy) {
  renderSelections(data.selections, copy);
  document.addEventListener("blend-select", async event => {
    const error = document.querySelector("#blend-error");
    error.hidden = true;
    try {
      const response = await fetch(settings.routes.selection, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(event.detail),
      });
      if (!response.ok) throw new Error(String(response.status));
      const selection = await response.json();
      data.selections = data.selections.filter(saved => saved.direction !== selection.direction);
      data.selections.push(selection);
      renderSelections(data.selections, copy);
    } catch {
      error.textContent = copy.blend.error.m;
      error.hidden = false;
    }
  });
}
