export function attachBlends(mappings, blends, policy) {
  const registry = new Map(blends.map(blend => [blend.id, blend]));
  return mappings.map(mapping => {
    const targets = mapping.targets.map(target => registry.get(target.id) ?? target);
    const blend = targets.some(target => target.kind === policy.blendKind);
    return { ...mapping, targets, action: blend ? policy.blendAction : mapping.action };
  });
}

export function changesPairs(mapping, policy) {
  if (policy.excludedSourcePrefixes.some(prefix => mapping.source_id.startsWith(prefix))) return false;
  return mapping.targets.length > 0 && mapping.targets.every(target => [policy.changedKind, policy.blendKind].includes(target.kind));
}

export function scopedMappings(mappings, policy) {
  return mappings.map(mapping => changesPairs(mapping, policy) ? mapping : {
    ...mapping, action: policy.unchangedAction, targets: [],
  });
}
