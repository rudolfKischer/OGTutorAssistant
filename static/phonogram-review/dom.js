export function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

export function textAt(copy, path) {
  return path.split(".").reduce((value, key) => value[key], copy);
}

export function fill(template, values) {
  return template.replace(/\{(\w+)\}/g, (_, key) => values[key]);
}

export function applyCopy(copy) {
  document.querySelectorAll("[data-copy]").forEach(element => {
    element.textContent = textAt(copy, element.dataset.copy);
  });
  document.querySelectorAll("[data-placeholder]").forEach(element => {
    element.placeholder = textAt(copy, element.dataset.placeholder);
  });
  document.title = copy.hd.t;
}

export async function readJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(String(response.status));
  return response.json();
}
