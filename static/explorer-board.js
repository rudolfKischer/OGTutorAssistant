const WE_MINUS = '\u2212';
const weExpandedTails = new Set();

function weNumber(n) {
  return n.toLocaleString();
}

function weCountInfo(id) {
  const dc = weDynamicCounts?.concepts;
  const only = weMode === 'only' && weFeatures.length > 0;
  if (only && weFeatures.includes(id)) {
    const marginal = dc?.[id + '_remove'] || 0;
    return { text: marginal ? WE_MINUS + weNumber(marginal) : '', cls: 'neg' };
  }
  if (only) {
    const gain = dc?.[id] || 0;
    return { text: '+' + weNumber(gain), cls: gain ? 'pos' : 'zero' };
  }
  const count = dc && dc[id] !== undefined ? dc[id] : (dc && weSettingsActive() ? 0 : weCatalog[id] || 0);
  return { text: weNumber(count), cls: '' };
}

function weCardHtml(id) {
  const selected = weFeatures.includes(id) ? ' selected' : '';
  const info = weCountInfo(id);
  const count = weDisplay.counts ? `<span class="pg-count ${info.cls}">${info.text}</span>` : '';
  const title = `${CONCEPT_LABELS[id] || id} · ${(weCatalog[id] || 0).toLocaleString()}`;
  return `<div class="pg-card${selected}" data-token="${id}" title="${title}">${wePillHtml(id)}${count}</div>`;
}

function weClusters(fam, ids) {
  if (!fam.ids) return [ids];
  const groups = new Map();
  ids.forEach(id => {
    const key = weMeta[id].sounds.join('+');
    groups.set(key, [...(groups.get(key) || []), id]);
  });
  return [...groups.values()];
}

function weSplitTail(ids) {
  const isTail = id => weMeta[id]?.tail;
  return { main: ids.filter(id => !isTail(id)), tail: ids.filter(isTail) };
}

function weClusterHtml(fam, ids, extra = '') {
  return weClusters(fam, ids).map(cluster => `<div class="pg-cluster${extra}">${cluster.map(weCardHtml).join('')}</div>`).join('');
}

function weFamilyHtml({ fam, ids }) {
  const { main, tail } = weSplitTail(ids);
  const allSelected = ids.every(id => weFeatures.includes(id));
  const collapsed = fam.collapsed && !weExpandedFamilies.has(fam.id);
  const tailOpen = weExpandedTails.has(fam.id);
  const more = fam.collapsed
    ? `<span class="we-row-toggle" onclick="weToggleCollapse('${fam.id}')">${collapsed ? `+${ids.length} more` : 'less'}</span>` : '';
  const copy = UI.explorerDisplay;
  const rare = tail.length
    ? `<span class="we-row-toggle" title="${copy.tailHint.replace('{count}', weNumber(tail.length))}" onclick="weToggleTail('${fam.id}')">${tailOpen ? copy.tailHide : '+' + weNumber(tail.length) + ' ' + copy.tailShow}</span>` : '';
  const body = weClusterHtml(fam, main) + (tailOpen ? weClusterHtml(fam, tail, ' tail') : '');
  return `<div class="we-row"><div class="we-row-hdr"><span class="we-row-label">${fam.label}</span>${more}${rare}
    <span class="we-row-toggle" title="${allSelected ? copy.deselectHint : copy.selectHint}" onclick="weToggleFamily('${fam.id}')">${allSelected ? copy.deselectAll : copy.selectAll}</span></div>
    <div class="pg-clusters"${collapsed ? ' style="display:none"' : ''}>${body}</div></div>`;
}

window.weToggleTail = function(famId) {
  if (weExpandedTails.has(famId)) weExpandedTails.delete(famId);
  else weExpandedTails.add(famId);
  weRenderBoard();
};

document.addEventListener('click', event => {
  const target = event.target.closest('[data-token]');
  if (!target) return;
  if (target.closest('#we-board')) weToggleFeature(target.dataset.token);
  else if (target.closest('#we-detail')) weToggleFeature(target.dataset.token);
});

function weRenderBoard() {
  const el = document.getElementById('we-board');
  const scroll = el.scrollTop;
  let html = '';
  let lastGroup = null;
  weVisibleFamilies().forEach(entry => {
    if (entry.fam.group && entry.fam.group !== lastGroup) {
      lastGroup = entry.fam.group;
      html += `<div class="we-group-hdr">${lastGroup}</div>`;
    }
    html += weFamilyHtml(entry);
  });
  el.innerHTML = html;
  el.scrollTop = scroll;
}

function weUpdateBoard() {
  weRenderBoard();
}
