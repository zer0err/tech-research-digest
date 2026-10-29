const test = require('node:test');
const assert = require('node:assert/strict');
const progress = require('../docs/assets/course-progress.js');

const TIME = '2026-10-27T02:00:00.000Z';
const lesson = (id = 'one', version = '1.0.0', compatible = []) => ({ lesson_id: id, content_version: version, compatible_versions: compatible });
const record = (series = 'basics', id = 'one', version = '1.0.0', at = TIME) => ({ series_id: series, lesson_id: id, content_version: version, completed_at: at });
const bundle = (records) => JSON.stringify({ schema_version: 1, records });
const exerciseRecord = (exerciseId = 'practice-one', series = 'basics', id = 'one', version = '1.0.0', at = TIME) => ({ ...record(series, id, version, at), exercise_id: exerciseId });
const bundleV2 = (records) => JSON.stringify({ schema_version: 2, records });
function memoryStorage(initial = null) {
  return {
    value: initial, writes: 0,
    getItem(key) { assert.equal(key, progress.STORAGE_KEY); return this.value; },
    setItem(key, value) { assert.equal(key, progress.STORAGE_KEY); this.value = value; this.writes += 1; },
  };
}
const store = (storage) => progress.createStore(storage, { clock: () => TIME });

test('opening a course does not create completion data; only manual toggles persist', () => {
  const storage = memoryStorage();
  const state = store(storage);
  assert.equal(storage.writes, 0);
  assert.deepEqual(state.snapshot(), { mode: 'persistent', records: [] });
  state.toggle('basics', lesson(), true);
  assert.deepEqual(JSON.parse(storage.value), { schema_version: 2, records: [record()] });
  state.toggle('basics', lesson(), false);
  assert.deepEqual(state.snapshot().records, []);
});

test('compatible completion counts once; breaking revisions retain history and suggest relearning', () => {
  const state = store(memoryStorage(bundle([record()])));
  assert.deepEqual(progress.lessonState(state.snapshot().records, 'basics', lesson('one', '1.0.1', ['1.0.0'])), { completed: true, compatible: true, outdated: false });
  assert.deepEqual(progress.lessonState(state.snapshot().records, 'basics', lesson('one', '2.0.0')), { completed: false, compatible: false, outdated: true });
  state.toggle('basics', lesson('one', '2.0.0'), true);
  assert.equal(state.snapshot().records.length, 2);
  state.toggle('basics', lesson('one', '2.0.0'), false);
  assert.deepEqual(state.snapshot().records, [record()]);
});

test('unchecking compatible completion removes that completion but keeps incompatible history', () => {
  const state = store(memoryStorage(bundle([record('basics', 'one', '0.5.0'), record()])));
  state.toggle('basics', lesson('one', '1.0.1', ['1.0.0']), false);
  assert.deepEqual(state.snapshot().records, [record('basics', 'one', '0.5.0')]);
});

test('summary deduplicates sidebar and lesson footer; only current or compatible versions count', () => {
  const lessons = [lesson(), lesson(), lesson('two'), lesson('three', '2.0.0')];
  assert.deepEqual(progress.summarize([record(), record('basics', 'three')], 'basics', lessons), { total: 3, completed: 1, percent: 33 });
  assert.throws(() => progress.summarize([], 'basics', [lesson(), lesson('one', '2.0.0')]), progress.ProgressError);
});

test('each mutation rereads latest storage to preserve sequential edits from other tabs', () => {
  const storage = memoryStorage();
  const a = store(storage);
  const b = store(storage);
  a.toggle('basics', lesson('one'), true);
  b.toggle('basics', lesson('two'), true);
  assert.equal(JSON.parse(storage.value).records.length, 2);
  a.toggle('basics', lesson('three'), true);
  assert.equal(JSON.parse(storage.value).records.length, 3);
  b.refresh();
  assert.equal(b.snapshot().records.length, 3);
});

test('clear is series-scoped and rereads other tabs before writing', () => {
  const storage = memoryStorage(bundle([record(), record('other')]));
  const a = store(storage);
  store(storage).toggle('other', lesson('two'), true);
  a.clearSeries('basics');
  assert.equal(a.snapshot().records.length, 2);
  assert.ok(a.snapshot().records.every((r) => r.series_id === 'other'));
});

test('strict import rejects extra fields, invalid ids/dates, duplicates, versions and oversize files atomically', () => {
  const storage = memoryStorage(bundle([record()]));
  const state = store(storage);
  const initial = storage.value;
  const invalid = [
    '{', 'null', '[]', JSON.stringify({ schema_version: 3, records: [] }),
    JSON.stringify({ schema_version: 1, records: [], email: 'unwanted' }),
    bundle([{ ...record(), email: 'unwanted' }]), bundle([{ ...record(), series_id: '../escape' }]),
    bundle([{ ...record(), lesson_id: '<img src=x>' }]), bundle([{ ...record(), content_version: null }]),
    bundle([{ ...record(), completed_at: '2026-02-31T02:00:00.000Z' }]),
    bundle([{ ...record(), completed_at: 'yesterday' }]), bundle([record(), record()]),
    JSON.stringify({ schema_version: 1, records: Array(progress.MAX_RECORDS + 1).fill(record()) }),
    ' '.repeat(progress.MAX_BYTES + 1),
  ];
  for (const text of invalid) {
    assert.throws(() => state.importText(text), progress.ProgressError);
    assert.equal(storage.value, initial);
    assert.deepEqual(state.snapshot().records, [record()]);
  }
  assert.equal(storage.writes, 0);
});

test('import merges by series, lesson and content version and keeps later timestamps', () => {
  const oldTime = '2026-10-26T02:00:00.000Z';
  const state = store(memoryStorage(bundle([record('basics', 'one', '1.0.0', oldTime), record('other')])));
  state.importText(bundle([record(), record('basics', 'one', '2.0.0')]));
  assert.equal(state.snapshot().records.length, 3);
  assert.equal(state.snapshot().records[0].completed_at, TIME);
  state.importText(bundle([record('basics', 'one', '1.0.0', oldTime)]));
  assert.equal(state.snapshot().records[0].completed_at, TIME);
  assert.deepEqual(progress.parseDocument(state.exportText()).records, state.snapshot().records);
});

test('series-scoped backup excludes other series and scoped import rejects them atomically', () => {
  const storage = memoryStorage(bundle([record(), record('other')]));
  const state = store(storage);
  assert.deepEqual(JSON.parse(state.exportText('basics')).records, [record()]);
  const initial = storage.value;
  assert.throws(() => state.importText(bundle([record('basics', 'two'), record('other')]), 'basics'), /其他系列/);
  assert.equal(storage.value, initial);
  assert.equal(storage.writes, 0);
  state.importText(bundle([record('basics', 'two')]), 'basics');
  assert.equal(state.snapshot().records.length, 3);
});

test('merged-size bound rejects whole import without altering valid existing progress', () => {
  const records = Array.from({ length: progress.MAX_RECORDS }, (_, n) => record('basics', 'unit-' + n));
  const storage = memoryStorage(bundle(records));
  const state = store(storage);
  const initial = storage.value;
  assert.throws(() => state.importText(bundle([record('other')])), progress.ProgressError);
  assert.equal(storage.value, initial);
  assert.equal(state.snapshot().records.length, progress.MAX_RECORDS);
});

test('storage unavailability still allows page-session toggles and export', () => {
  for (const storage of [null, { getItem() { throw new Error('blocked'); } }]) {
    const state = store(storage);
    state.toggle('basics', lesson(), true);
    assert.equal(state.snapshot().mode, 'session');
    assert.deepEqual(progress.parseDocument(state.exportText()).records, [record()]);
    state.toggle('basics', lesson('two'), true);
    assert.equal(state.snapshot().records.length, 2);
  }
});

test('quota failure retains all subsequent session edits without overwriting stored backup', () => {
  const storage = memoryStorage(bundle([record()]));
  storage.setItem = () => { throw new Error('quota'); };
  const state = store(storage);
  state.toggle('basics', lesson('two'), true);
  state.toggle('basics', lesson('three'), true);
  state.refresh();
  assert.equal(state.snapshot().mode, 'session');
  assert.equal(state.snapshot().records.length, 3);
  assert.deepEqual(JSON.parse(storage.value).records, [record()]);
});

test('corrupted stored data is not silently replaced by toggles, clear, or import', () => {
  const storage = memoryStorage('{invalid');
  const state = store(storage);
  state.toggle('basics', lesson(), true);
  state.clearSeries('basics');
  state.importText(bundle([record('other')]));
  assert.equal(state.snapshot().mode, 'corrupt');
  assert.equal(storage.value, '{invalid');
  assert.equal(storage.writes, 0);
  assert.deepEqual(state.snapshot().records, [record('other')]);
  assert.equal(state.rawCorruptText(), '{invalid');
});

test('a corruption introduced after load preserves last good snapshot and original corrupt text', () => {
  const storage = memoryStorage(bundle([record()]));
  const state = store(storage);
  storage.value = 'broken';
  state.toggle('basics', lesson('two'), true);
  assert.equal(state.snapshot().records.length, 2);
  assert.equal(state.snapshot().mode, 'corrupt');
  assert.equal(storage.value, 'broken');
});

test('snapshots are defensive copies and exported schema contains no user identifier', () => {
  const state = store(memoryStorage(bundle([record()])));
  state.snapshot().records[0].series_id = 'mutated';
  assert.equal(state.snapshot().records[0].series_id, 'basics');
  assert.deepEqual(Object.keys(JSON.parse(state.exportText()).records[0]).sort(), ['completed_at', 'content_version', 'lesson_id', 'series_id']);
});

test('schema 1 completion loads without writing and migrates to schema 2 on explicit export or mutation', () => {
  const original = bundle([record()]);
  const storage = memoryStorage(original);
  const state = store(storage);
  assert.equal(storage.writes, 0);
  assert.equal(storage.value, original);
  assert.equal(progress.lessonState(state.snapshot().records, 'basics', lesson()).completed, true);
  assert.equal(progress.exerciseState(state.snapshot().records, 'basics', lesson(), 'practice-one').completed, false);
  assert.deepEqual(JSON.parse(state.exportText('basics')), { schema_version: 2, records: [record()] });
  assert.equal(storage.writes, 0);
  state.toggleExercise('basics', lesson(), 'practice-one', true);
  assert.equal(JSON.parse(storage.value).schema_version, 2);
  assert.equal(state.snapshot().records.length, 2);
});

test('exercise and whole-lesson completion never infer or cancel each other', () => {
  const state = store(memoryStorage());
  state.toggleExercise('basics', lesson(), 'practice-one', true);
  state.toggleExercise('basics', lesson(), 'practice-two', true);
  assert.equal(progress.lessonState(state.snapshot().records, 'basics', lesson()).completed, false);
  state.toggle('basics', lesson(), true);
  state.toggleExercise('basics', lesson(), 'practice-one', false);
  assert.equal(progress.lessonState(state.snapshot().records, 'basics', lesson()).completed, true);
  assert.equal(progress.exerciseState(state.snapshot().records, 'basics', lesson(), 'practice-one').completed, false);
  assert.equal(progress.exerciseState(state.snapshot().records, 'basics', lesson(), 'practice-two').completed, true);
  state.toggle('basics', lesson(), false);
  assert.deepEqual(state.snapshot().records, [exerciseRecord('practice-two')]);
});

test('exercise version compatibility is independent of lesson records and preserves incompatible history', () => {
  const state = store(memoryStorage(bundleV2([record(), exerciseRecord()])));
  const compatible = lesson('one', '1.0.1', ['1.0.0']);
  const breaking = lesson('one', '2.0.0');
  assert.deepEqual(progress.exerciseState(state.snapshot().records, 'basics', compatible, 'practice-one'), { completed: true, compatible: true, outdated: false });
  assert.deepEqual(progress.exerciseState(state.snapshot().records, 'basics', breaking, 'practice-one'), { completed: false, compatible: false, outdated: true });
  state.toggleExercise('basics', breaking, 'practice-one', true);
  state.toggleExercise('basics', breaking, 'practice-one', false);
  assert.equal(state.snapshot().records.length, 2);
  state.toggleExercise('basics', compatible, 'practice-one', false);
  assert.deepEqual(state.snapshot().records, [record()]);
});

test('strict exercise records reject invalid ids, extras, duplicates, and schema 1 disguise atomically', () => {
  const storage = memoryStorage(bundle([record()]));
  const state = store(storage);
  const invalid = [
    bundle([exerciseRecord()]),
    bundleV2([{ ...exerciseRecord(), exercise_id: null }]),
    bundleV2([{ ...exerciseRecord(), exercise_id: '' }]),
    bundleV2([{ ...exerciseRecord(), exercise_id: '../x' }]),
    bundleV2([{ ...exerciseRecord(), exercise_id: '<script>' }]),
    bundleV2([{ ...exerciseRecord(), exercise_id: 12 }]),
    bundleV2([{ ...exerciseRecord(), user: 'unknown' }]),
    bundleV2([exerciseRecord(), exerciseRecord()]),
  ];
  for (const text of invalid) assert.throws(() => state.importText(text, 'basics'), progress.ProgressError);
  assert.equal(storage.writes, 0);
  assert.deepEqual(state.snapshot().records, [record()]);
});

test('exercise summaries deduplicate each lesson/exercise pair but keep different lessons separate', () => {
  const exercise = { ...lesson(), exercise_id: 'practice-one' };
  const other = { ...lesson('two'), exercise_id: 'practice-one' };
  assert.deepEqual(progress.summarizeExercises([exerciseRecord(), record('basics', 'two')], 'basics', [exercise, exercise, other]), { total: 2, completed: 1, percent: 50 });
  assert.throws(() => progress.summarizeExercises([], 'basics', [exercise, { ...exercise, content_version: '2.0.0' }]), progress.ProgressError);
});

test('series backups merge old lesson records with exercises and clear both types without affecting other series', () => {
  const state = store(memoryStorage(bundleV2([exerciseRecord(), exerciseRecord('practice-one', 'other')])));
  state.importText(bundle([record()]), 'basics');
  assert.equal(state.snapshot().records.length, 3);
  const backup = JSON.parse(state.exportText('basics'));
  assert.equal(backup.schema_version, 2);
  assert.equal(backup.records.length, 2);
  assert.ok(backup.records.every((item) => item.series_id === 'basics'));
  state.clearSeries('basics');
  assert.deepEqual(state.snapshot().records, [exerciseRecord('practice-one', 'other')]);
});

test('sequential tabs preserve exercise and lesson mutations and do not confuse identical ids', () => {
  const storage = memoryStorage();
  const a = store(storage); const b = store(storage);
  a.toggleExercise('basics', lesson(), 'lesson', true);
  b.toggle('basics', lesson(), true);
  a.toggleExercise('basics', lesson(), 'practice-two', true);
  b.refresh();
  assert.equal(b.snapshot().records.length, 3);
  assert.equal(progress.lessonState(b.snapshot().records, 'basics', lesson()).completed, true);
  assert.equal(progress.exerciseState(b.snapshot().records, 'basics', lesson(), 'lesson').completed, true);
});

test('exercise toggles remain usable in memory-only mode without overwriting corrupt originals', () => {
  for (const storage of [null, memoryStorage('corrupt')]) {
    const state = store(storage);
    state.toggleExercise('basics', lesson(), 'practice-one', true);
    assert.deepEqual(JSON.parse(state.exportText('basics')).records, [exerciseRecord()]);
    if (storage) { assert.equal(storage.value, 'corrupt'); assert.equal(storage.writes, 0); }
  }
});

class Element {
  constructor(dataset = {}) { this.dataset = dataset; this.handlers = {}; this.nodes = {}; this.disabled = true; this.checked = false; this.textContent = ''; }
  querySelectorAll(selector) { return this.nodes[selector] || []; }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  closest(selector) { return selector === '[data-course-lesson]' ? this.lessonAncestor || null : null; }
  addEventListener(type, callback) { this.handlers[type] = callback; }
  async fire(type) { if (this.handlers[type]) return this.handlers[type]({ target: this }); }
  click() { this.clicked = true; }
}

function fixture(storage = memoryStorage()) {
  const root = new Element({ seriesId: 'basics', contentVersion: '1.0.0' });
  const one = new Element({ lessonId: 'one', contentVersion: '1.0.0' });
  const duplicate = new Element({ lessonId: 'one', contentVersion: '1.0.0' });
  const two = new Element({ lessonId: 'two', contentVersion: '1.0.0' });
  const checkbox = new Element();
  const status = new Element();
  one.nodes['[data-lesson-status]'] = [status];
  duplicate.nodes['[data-course-complete]'] = [checkbox];
  root.nodes['[data-course-lesson]'] = [one, two, duplicate];
  const exerciseSummary = new Element();
  duplicate.nodes['[data-exercise-summary]'] = [exerciseSummary];
  const exerciseOne = new Element({ exerciseId: 'practice-one' });
  const exerciseTwo = new Element({ exerciseId: 'practice-two' });
  const exerciseCheckbox = new Element(); const exerciseCheckboxTwo = new Element();
  const exerciseStatus = new Element();
  exerciseOne.lessonAncestor = duplicate; exerciseTwo.lessonAncestor = duplicate;
  exerciseOne.nodes['[data-exercise-complete]'] = [exerciseCheckbox];
  exerciseTwo.nodes['[data-exercise-complete]'] = [exerciseCheckboxTwo];
  exerciseOne.nodes['[data-exercise-status]'] = [exerciseStatus];
  root.nodes['[data-course-exercise]'] = [exerciseOne, exerciseTwo];
  const summary = new Element(); const meter = new Element(); const notice = new Element();
  const clear = new Element(); const file = new Element(); const importButton = new Element();
  const exportButton = new Element(); const rawButton = new Element();
  root.nodes['[data-progress-summary]'] = [summary];
  root.nodes['progress[data-progress-meter]'] = [meter];
  root.nodes['[data-progress-notice]'] = [notice];
  root.nodes['[data-progress-clear]'] = [clear];
  root.nodes['[data-progress-import]'] = [importButton];
  root.nodes['[data-progress-export]'] = [exportButton];
  root.nodes['[data-progress-export-raw]'] = [rawButton];
  root.nodes['input[type="file"][data-progress-file]'] = [file];
  const downloads = []; const blobs = []; const revoked = [];
  const doc = new Element(); doc.nodes['[data-course-progress]'] = [root];
  doc.body = { appendChild() {} };
  doc.createElement = (name) => {
    assert.equal(name, 'a');
    return { click() { downloads.push({ href: this.href, filename: this.download }); }, remove() {} };
  };
  const win = { localStorage: storage, location: { protocol: 'https:' }, handlers: {}, confirm: () => true,
    Blob: class { constructor(parts, options) { this.parts = parts; this.type = options.type; } },
    URL: { createObjectURL(blob) { blobs.push(blob); return 'blob:local-' + blobs.length; }, revokeObjectURL(url) { revoked.push(url); } },
    setTimeout(callback) { callback(); },
    addEventListener(type, handler) { this.handlers[type] = handler; } };
  const app = progress.initialize(doc, win);
  return { root, storage, checkbox, status, summary, meter, notice, clear, file, importButton, exportButton, rawButton, downloads, blobs, revoked, win, app,
    exerciseOne, exerciseTwo, exerciseCheckbox, exerciseCheckboxTwo, exerciseStatus, exerciseSummary };
}

test('DOM initializes disabled controls, deduplicates items, and only change events complete lessons', async () => {
  const f = fixture();
  assert.equal(f.checkbox.disabled, false);
  assert.equal(f.storage.writes, 0);
  assert.match(f.summary.textContent, /0 \/ 2/);
  f.checkbox.checked = true;
  await f.checkbox.fire('change');
  assert.match(f.summary.textContent, /1 \/ 2.*50%/);
  assert.equal(f.meter.value, 50);
  assert.equal(f.status.textContent, '已完成');
  assert.equal(f.storage.writes, 1);
});

test('DOM confirms series clearing and storage events synchronize completion', async () => {
  const f = fixture(memoryStorage(bundle([record(), record('other')])));
  f.win.confirm = () => false;
  await f.clear.fire('click');
  assert.equal(f.checkbox.checked, true);
  f.win.confirm = () => true;
  await f.clear.fire('click');
  assert.equal(f.checkbox.checked, false);
  assert.deepEqual(JSON.parse(f.storage.value).records, [record('other')]);
  f.storage.value = bundle([record()]);
  f.win.handlers.storage({ key: progress.STORAGE_KEY, storageArea: f.storage });
  assert.equal(f.checkbox.checked, true);
  f.storage.value = null;
  f.win.handlers.storage({ key: null, storageArea: f.storage });
  assert.equal(f.checkbox.checked, false);
});

test('DOM import validates before confirmation, supports cancellation and does not inject markup', async () => {
  const f = fixture();
  let confirmations = 0;
  f.win.confirm = () => { confirmations += 1; return false; };
  f.file.files = [{ size: 10, text: async () => bundle([{ ...record(), lesson_id: '<img onerror=x>' }]) }];
  await f.file.fire('change');
  assert.equal(confirmations, 0);
  assert.equal(f.storage.writes, 0);
  assert.match(f.notice.textContent, /无效记录/);
  f.file.files = [{ size: 10, text: async () => bundle([record()]) }];
  await f.file.fire('change');
  assert.equal(confirmations, 1);
  assert.equal(f.storage.writes, 0);
  f.win.confirm = () => true;
  await f.file.fire('change');
  assert.equal(f.storage.writes, 1);
  assert.equal(f.checkbox.checked, true);
});

test('DOM rejects another series before asking for confirmation', async () => {
  const f = fixture();
  f.win.confirm = () => { throw new Error('must not ask'); };
  f.file.files = [{ size: 100, text: async () => bundle([record('other')]) }];
  await f.file.fire('change');
  assert.match(f.notice.textContent, /其他系列/);
  assert.equal(f.storage.writes, 0);
});

test('DOM bounds file size before reading and leaves storage unchanged', async () => {
  const f = fixture();
  f.file.files = [{ size: progress.MAX_BYTES + 1, text: async () => { throw new Error('must not read'); } }];
  await f.file.fire('change');
  assert.match(f.notice.textContent, /文件过大/);
  assert.equal(f.storage.writes, 0);
});

test('DOM export creates only a local series-scoped download and revokes its URL', async () => {
  const f = fixture(memoryStorage(bundle([record(), record('other')])));
  assert.equal(f.rawButton.hidden, true);
  assert.equal(f.rawButton.disabled, true);
  await f.exportButton.fire('click');
  assert.equal(f.downloads.length, 1);
  assert.match(f.downloads[0].filename, /^vorasio-basics-progress-\d{4}-\d\d-\d\d\.json$/);
  assert.deepEqual(JSON.parse(f.blobs[0].parts[0]).records, [record()]);
  assert.deepEqual(f.revoked, ['blob:local-1']);
  assert.equal(f.storage.writes, 0);
});

test('DOM offers separate damaged-original export without destroying safe session progress', async () => {
  const f = fixture(memoryStorage('{damaged'));
  assert.equal(f.rawButton.hidden, false);
  assert.equal(f.rawButton.disabled, false);
  f.checkbox.checked = true;
  await f.checkbox.fire('change');
  await f.rawButton.fire('click');
  assert.equal(f.blobs[0].parts[0], '{damaged');
  assert.equal(f.downloads[0].filename, 'vorasio-damaged-progress-original.txt');
  await f.exportButton.fire('click');
  assert.equal(JSON.parse(f.blobs[1].parts[0]).records.length, 1);
  assert.equal(f.storage.value, '{damaged');
  assert.equal(f.storage.writes, 0);
});

test('DOM displays explicit warnings while session-only controls remain usable', async () => {
  const f = fixture(memoryStorage('damaged'));
  assert.match(f.notice.textContent, /原数据未被覆盖/);
  f.checkbox.checked = true;
  await f.checkbox.fire('change');
  assert.equal(f.checkbox.checked, true);
  assert.equal(f.storage.value, 'damaged');
  assert.equal(f.storage.writes, 0);
});

test('DOM exercise checkboxes enable on init and remain separate from whole-lesson completion', async () => {
  const f = fixture();
  assert.equal(f.exerciseCheckbox.disabled, false);
  assert.equal(f.exerciseCheckbox.checked, false);
  assert.match(f.exerciseSummary.textContent, /0 \/ 2 项练习/);
  assert.equal(f.storage.writes, 0);
  f.exerciseCheckbox.checked = true;
  await f.exerciseCheckbox.fire('change');
  assert.equal(f.exerciseStatus.textContent, '已完成');
  assert.match(f.exerciseSummary.textContent, /1 \/ 2 项练习/);
  assert.match(f.summary.textContent, /0 \/ 2 个单元/);
  f.exerciseCheckboxTwo.checked = true;
  await f.exerciseCheckboxTwo.fire('change');
  assert.equal(f.checkbox.checked, false);
  assert.match(f.exerciseSummary.textContent, /2 \/ 2 项练习/);
  f.checkbox.checked = true;
  await f.checkbox.fire('change');
  f.exerciseCheckbox.checked = false;
  await f.exerciseCheckbox.fire('change');
  assert.equal(f.checkbox.checked, true);
  assert.match(f.summary.textContent, /1 \/ 2 个单元/);
});

test('DOM old whole-lesson record does not mark exercises complete; storage events synchronize both kinds', () => {
  const f = fixture(memoryStorage(bundle([record()])));
  assert.equal(f.checkbox.checked, true);
  assert.equal(f.exerciseCheckbox.checked, false);
  assert.match(f.exerciseSummary.textContent, /0 \/ 2 项练习/);
  assert.equal(f.storage.writes, 0);
  f.storage.value = bundleV2([exerciseRecord()]);
  f.win.handlers.storage({ key: progress.STORAGE_KEY, storageArea: f.storage });
  assert.equal(f.checkbox.checked, false);
  assert.equal(f.exerciseCheckbox.checked, true);
  assert.match(f.exerciseSummary.textContent, /1 \/ 2 项练习/);
});

test('DOM scoped export includes exercise records and clear removes both exercise and lesson flags', async () => {
  const f = fixture(memoryStorage(bundleV2([record(), exerciseRecord(), exerciseRecord('practice-one', 'other')])));
  await f.exportButton.fire('click');
  const backup = JSON.parse(f.blobs[0].parts[0]);
  assert.equal(backup.schema_version, 2);
  assert.equal(backup.records.length, 2);
  await f.clear.fire('click');
  assert.equal(f.checkbox.checked, false);
  assert.equal(f.exerciseCheckbox.checked, false);
  assert.deepEqual(JSON.parse(f.storage.value).records, [exerciseRecord('practice-one', 'other')]);
});
