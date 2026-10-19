const WE_SCALE_STEP = 500;
const WE_SCALE_TOP = 67423;
let weRankScale = {};
let weScalePromise = null;

function weSliderConfig(id) {
  return weSettingsCopy().sliders[id];
}

function weSliderSteps(id) {
  const slider = weSliderConfig(id);
  return Math.round((slider.max - slider.min) / slider.step);
}

function weSliderValue(id, position) {
  if (weSliderConfig(id).offAtEnd && position === weSliderSteps(id)) return 0;
  return weSliderConfig(id).min + position * weSliderConfig(id).step;
}

function weSliderPosition(id, value) {
  const slider = weSliderConfig(id);
  if (!value && slider.offAtEnd) return weSliderSteps(id);
  return Math.round((Math.min(slider.max, Math.max(slider.min, value)) - slider.min) / slider.step);
}

function weSliderText(id, value) {
  const slider = weSliderConfig(id);
  if (!value) return slider.offLabel || slider.valueTemplate.replace('{value}', slider.min.toLocaleString());
  return slider.valueTemplate.replace('{value}', value.toLocaleString());
}

function weSliderCaption(id, value) {
  const info = weRankScale[String(value)];
  if (id === 'rare' || !value || !info || info.rank === null) return null;
  return `${fmtFreq(info.per_million)} · #${info.rank.toLocaleString()} · ${info.examples.join(', ')}`;
}

function weSliderFill(input) {
  input.style.setProperty('--fill', `${(Number(input.value) / Number(input.max)) * 100}%`);
}

function weRenderSlider(id, value) {
  document.getElementById(`we-value-${id}`).textContent = weSliderText(id, value);
  const caption = id === 'rare' || !value ? '' : weSliderCaption(id, value);
  if (caption !== null) document.getElementById(`we-caption-${id}`).textContent = caption;
}

function weLoadScale() {
  if (weScalePromise) return weScalePromise;
  const ranks = [];
  for (let rank = WE_SCALE_STEP; rank < WE_SCALE_TOP; rank += WE_SCALE_STEP) ranks.push(rank);
  weScalePromise = fetch(`/api/rank-scale?ranks=${ranks.join(',')}`).then(response => response.json()).then(data => Object.assign(weRankScale, data));
  return weScalePromise;
}

function weSliderRowHtml(id) {
  const slider = weSliderConfig(id);
  return `<div class="pg-set-slider"><div class="pg-set-line"><span class="pg-set-name" data-tip="${slider.hint}">${slider.label}<i>i</i></span>
    <span class="pg-set-value" id="we-value-${id}"></span></div>
    <input type="range" min="0" max="${weSliderSteps(id)}" step="1" data-slider="${id}"><div class="pg-set-caption" id="we-caption-${id}"></div></div>`;
}

function weSyncSliders(panel) {
  panel.querySelectorAll('[data-slider]').forEach(input => {
    const id = input.dataset.slider;
    input.value = weSliderPosition(id, weDraft[id]);
    weSliderFill(input);
    weRenderSlider(id, weDraft[id]);
  });
}

function weBindSliders(panel, onChange) {
  panel.querySelectorAll('[data-slider]').forEach(input => {
    const id = input.dataset.slider;
    input.addEventListener('input', () => { weSliderFill(input); weRenderSlider(id, weSliderValue(id, Number(input.value))); });
    input.addEventListener('change', () => onChange(id, weSliderValue(id, Number(input.value))));
  });
  weLoadScale().then(() => weSyncSliders(panel));
}
