import { fill } from "./dom.js";

export function bindNotation(settings, copy, render) {
  const notation = settings.notation;
  notation.currentMode = notation.defaultMode;
  const button = document.querySelector("#notation");
  const update = () => {
    button.textContent = fill(copy.notation.cycle.a, { mode: copy.notation[notation.currentMode].l });
  };
  button.onclick = () => {
    const index = notation.modes.indexOf(notation.currentMode);
    notation.currentMode = notation.modes[(index + 1) % notation.modes.length];
    update();
    render();
    document.dispatchEvent(new CustomEvent("notation-change"));
  };
  update();
}
