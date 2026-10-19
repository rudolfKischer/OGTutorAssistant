import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repository = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const workspace = path.dirname(repository);
const assets = path.join(repository, 'static/phonogram-review');
const read = location => JSON.parse(fs.readFileSync(location, 'utf8'));
const settings = read(path.join(assets, 'settings.json'));
const source = fs.readFileSync(path.join(assets, 'scope.js'), 'utf8');
const { changesPairs, attachBlends } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const directory = path.join(workspace, 'notes/issue-10-phonograms');
const report = read(path.join(directory, 'phase-0/baseline.json'));
const blends = read(path.join(repository, "data/mappings/blend-phonograms.json"));
report.mapping.mappings = attachBlends(report.mapping.mappings, blends.definitions, settings.scope);
const action = mapping => mapping.targets.some(target => target.kind === settings.scope.blendKind)
  ? settings.scope.blendAction : settings.scope.changedAction;
const fields = ['namespace', 'source_id', 'source_name', 'action', 'target_ids', 'reading', 'spelling'];
const encode = value => `"${String(value).replaceAll('"', '""')}"`;
const rows = report.mapping.mappings.map(mapping => {
  const changed = changesPairs(mapping, settings.scope);
  return [mapping.namespace, mapping.source_id, mapping.source_name,
    changed ? action(mapping) : settings.scope.unchangedAction,
    JSON.stringify(changed ? mapping.targets.map(target => target.id) : [mapping.source_id]),
    changed ? mapping.decoding : 'preserve_existing', changed ? mapping.encoding : 'preserve_existing'];
});
const csv = [fields, ...rows].map(row => row.map(encode).join(',')).join('\n');
fs.writeFileSync(path.join(directory, 'MASTER-PLAN-SCOPED-ID-MAP.csv'), `${csv}\n`);
process.stdout.write(JSON.stringify({ sources: rows.length, pairChanges: rows.filter(row => row[3] === settings.scope.changedAction).length, blendMappings: rows.filter(row => row[3] === settings.scope.blendAction).length }));
const inventory = read(path.join(assets, 'inventories.json'));
const byRow = new Map(report.mapping.mappings.filter(mapping => mapping.namespace === settings.views.curriculumNamespace)
  .map(mapping => [Number(mapping.source_id), mapping]));
const curriculumFields = ['spreadsheet_row', 'original_name', 'group', 'subgroup', 'original_backend_id', 'status', 'proposed_pair_ids', 'source_conflict'];
const curriculumRows = inventory.curriculum.map(row => {
  const mapping = byRow.get(row.row);
  if (!mapping) throw new Error(`Unaccounted spreadsheet row ${row.row}`);
  const phonics = row.group === settings.views.phonicsGroup;
  const unresolved = phonics && mapping.targets.some(target => target.status === 'not_modeled');
  const changed = phonics && changesPairs(mapping, settings.scope);
  return [row.row, row.name, row.group, row.subgroup ?? '', row.legacy_id ?? '',
    unresolved ? 'unresolved' : changed ? action(mapping) : settings.scope.unchangedAction,
    JSON.stringify(changed ? mapping.targets.map(target => target.id) : []),
    mapping.targets.some(target => target.kind === settings.scope.blendKind
      && (row.grapheme !== target.spelling || row.legacy_id?.trim() !== target.id))];
});
fs.writeFileSync(path.join(directory, 'MASTER-PLAN-CURRICULUM-MAP.csv'),
  [curriculumFields, ...curriculumRows].map(row => row.map(encode).join(',')).join('\n') + '\n');
