(function (global) {
  'use strict';

  const STORAGE_KEY = 'vorasio.course-progress.v1';
  const SCHEMA_VERSION = 2;
  const MAX_RECORDS = 2000;
  const MAX_BYTES = 1024 * 1024;
  const ID = /^[a-z0-9][a-z0-9_-]{0,99}$/;
  const VERSION = /^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$/;
  const recordKeys = ['completed_at', 'content_version', 'lesson_id', 'series_id'];
  const exerciseRecordKeys = recordKeys.concat('exercise_id');

  class ProgressError extends Error {
    constructor(message) {
      super(message);
      this.name = 'ProgressError';
    }
  }

  function exactKeys(value, keys) {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      && Object.keys(value).sort().join(',') === keys.slice().sort().join(',');
  }

  function key(record) {
    return [record.series_id, record.lesson_id, record.exercise_id === undefined ? 'lesson' : 'exercise/' + record.exercise_id, record.content_version].join('/');
  }

  function validateSeries(seriesId) {
    if (typeof seriesId !== 'string' || !ID.test(seriesId)) throw new ProgressError('系列编号无效。');
  }

  function requireSeries(document, seriesId) {
    validateSeries(seriesId);
    if (document.records.some(function (record) { return record.series_id !== seriesId; })) {
      throw new ProgressError('文件包含其他系列的进度，未导入任何数据。请在对应系列页面导入该系列的备份。');
    }
    return document;
  }

  function validateDocument(value) {
    if (!exactKeys(value, ['schema_version', 'records']) || ![1, SCHEMA_VERSION].includes(value.schema_version)
      || !Array.isArray(value.records) || value.records.length > MAX_RECORDS) {
      throw new ProgressError('进度文件格式或版本不正确，或记录数量过多。');
    }
    const seen = new Set();
    const records = value.records.map(function (record) {
      const isExercise = value.schema_version === SCHEMA_VERSION && exactKeys(record, exerciseRecordKeys);
      if ((!exactKeys(record, recordKeys) && !isExercise)
        || (isExercise && (typeof record.exercise_id !== 'string' || !ID.test(record.exercise_id)))
        || typeof record.series_id !== 'string' || !ID.test(record.series_id)
        || typeof record.lesson_id !== 'string' || !ID.test(record.lesson_id)
        || typeof record.content_version !== 'string' || !VERSION.test(record.content_version)
        || typeof record.completed_at !== 'string'
        || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(record.completed_at)
        || !Number.isFinite(Date.parse(record.completed_at))
        || new Date(record.completed_at).toISOString() !== record.completed_at) {
        throw new ProgressError('进度文件含有无效记录，未导入任何数据。');
      }
      const identity = key(record);
      if (seen.has(identity)) throw new ProgressError('进度文件含有重复记录，未导入任何数据。');
      seen.add(identity);
      const clean = {
        series_id: record.series_id,
        lesson_id: record.lesson_id,
        content_version: record.content_version,
        completed_at: record.completed_at,
      };
      if (isExercise) clean.exercise_id = record.exercise_id;
      return clean;
    });
    records.sort(function (a, b) { return key(a).localeCompare(key(b)); });
    // Reading old lesson-only data migrates only the in-memory representation.
    // Opening a page never writes storage or infers exercise completion.
    return { schema_version: SCHEMA_VERSION, records: records };
  }

  function parseDocument(text) {
    if (typeof text !== 'string' || text.length > MAX_BYTES) {
      throw new ProgressError('进度文件过大，最多支持 1 MB。');
    }
    let value;
    try { value = JSON.parse(text); }
    catch (_) { throw new ProgressError('不是有效的 JSON 进度文件，未导入任何数据。'); }
    return validateDocument(value);
  }

  function validLesson(seriesId, lesson) {
    if (typeof seriesId !== 'string' || !ID.test(seriesId)
      || !lesson || typeof lesson.lesson_id !== 'string' || !ID.test(lesson.lesson_id)
      || typeof lesson.content_version !== 'string' || !VERSION.test(lesson.content_version)
      || !Array.isArray(lesson.compatible_versions)
      || lesson.compatible_versions.length > 100
      || !lesson.compatible_versions.every(function (version) {
        return typeof version === 'string' && VERSION.test(version);
      })) throw new ProgressError('课程进度配置无效，请联系网站维护者。');
  }

  function validExercise(seriesId, lesson, exerciseId) {
    validLesson(seriesId, lesson);
    if (typeof exerciseId !== 'string' || !ID.test(exerciseId)) throw new ProgressError('练习进度配置无效，请联系网站维护者。');
  }

  function completionState(records, seriesId, lesson, exerciseId) {
    validLesson(seriesId, lesson);
    const history = records.filter(function (record) {
      return record.series_id === seriesId && record.lesson_id === lesson.lesson_id
        && record.exercise_id === exerciseId;
    });
    const current = history.some(function (record) { return record.content_version === lesson.content_version; });
    const compatible = history.some(function (record) {
      return lesson.compatible_versions.includes(record.content_version);
    });
    return { completed: current || compatible, compatible: !current && compatible, outdated: !current && !compatible && history.length > 0 };
  }

  function lessonState(records, seriesId, lesson) {
    return completionState(records, seriesId, lesson, undefined);
  }

  function exerciseState(records, seriesId, lesson, exerciseId) {
    validExercise(seriesId, lesson, exerciseId);
    return completionState(records, seriesId, lesson, exerciseId);
  }

  function summarizeExercises(records, seriesId, exercises) {
    const unique = new Map();
    exercises.forEach(function (exercise) {
      validExercise(seriesId, exercise, exercise.exercise_id);
      const identity = exercise.lesson_id + '/' + exercise.exercise_id;
      const existing = unique.get(identity);
      if (existing && (existing.content_version !== exercise.content_version
        || existing.compatible_versions.join(',') !== exercise.compatible_versions.join(','))) {
        throw new ProgressError('重复练习的内容版本配置不一致。');
      }
      unique.set(identity, exercise);
    });
    const total = unique.size;
    const completed = Array.from(unique.values()).filter(function (exercise) {
      return exerciseState(records, seriesId, exercise, exercise.exercise_id).completed;
    }).length;
    return { total: total, completed: completed, percent: total ? Math.round(completed * 100 / total) : 0 };
  }

  function summarize(records, seriesId, lessons) {
    const unique = new Map();
    lessons.forEach(function (lesson) {
      validLesson(seriesId, lesson);
      const existing = unique.get(lesson.lesson_id);
      if (existing && (existing.content_version !== lesson.content_version
        || existing.compatible_versions.join(',') !== lesson.compatible_versions.join(','))) {
        throw new ProgressError('重复单元的内容版本配置不一致。');
      }
      unique.set(lesson.lesson_id, lesson);
    });
    const total = unique.size;
    const completed = Array.from(unique.values()).filter(function (lesson) {
      return lessonState(records, seriesId, lesson).completed;
    }).length;
    return { total: total, completed: completed, percent: total ? Math.round(completed * 100 / total) : 0 };
  }

  function createStore(storage, options) {
    const clock = options && options.clock ? options.clock : function () { return new Date().toISOString(); };
    let document = { schema_version: SCHEMA_VERSION, records: [] };
    let mode = 'persistent';
    let corruptRaw = null;

    function refresh() {
      // A failed or corrupt store stays in memory-only mode for this page session.
      // Never overwrite damaged data, or discard unsaved session edits on a later read.
      if (mode !== 'persistent') return snapshot();
      let raw;
      try {
        if (!storage) throw new Error('unavailable');
        raw = storage.getItem(STORAGE_KEY);
      } catch (_) { mode = 'session'; return snapshot(); }
      try { document = raw === null ? { schema_version: SCHEMA_VERSION, records: [] } : parseDocument(raw); }
      catch (_) { mode = 'corrupt'; corruptRaw = raw; }
      return snapshot();
    }

    function snapshot() {
      return { mode: mode, records: document.records.map(function (record) { return Object.assign({}, record); }) };
    }

    function write(records) {
      // Validate before replacing either the in-memory snapshot or persisted document.
      const candidate = validateDocument({ schema_version: SCHEMA_VERSION, records: records });
      const serialized = JSON.stringify(candidate);
      if (serialized.length > MAX_BYTES) throw new ProgressError('合并后的进度数据过大，未保存此次操作。');
      if (mode === 'persistent') {
        try { storage.setItem(STORAGE_KEY, serialized); }
        catch (_) { mode = 'session'; }
      }
      document = candidate;
      return snapshot();
    }

    function toggleCompletion(seriesId, lesson, completed, exerciseId) {
      validLesson(seriesId, lesson);
      if (exerciseId !== undefined) validExercise(seriesId, lesson, exerciseId);
      if (typeof completed !== 'boolean') throw new ProgressError('完成状态无效。');
      refresh(); // Read latest on each mutation: protects sequential edits in different tabs.
      let records = document.records.slice();
      if (completed) {
        const record = { series_id: seriesId, lesson_id: lesson.lesson_id, content_version: lesson.content_version, completed_at: clock() };
        if (exerciseId !== undefined) record.exercise_id = exerciseId;
        if (!records.some(function (item) { return key(item) === key(record); })) records.push(record);
      } else {
        records = records.filter(function (record) {
          return record.series_id !== seriesId || record.lesson_id !== lesson.lesson_id || record.exercise_id !== exerciseId
            || (record.content_version !== lesson.content_version && !lesson.compatible_versions.includes(record.content_version));
        });
      }
      return write(records);
    }

    function toggle(seriesId, lesson, completed) {
      return toggleCompletion(seriesId, lesson, completed, undefined);
    }

    function toggleExercise(seriesId, lesson, exerciseId, completed) {
      validExercise(seriesId, lesson, exerciseId);
      return toggleCompletion(seriesId, lesson, completed, exerciseId);
    }

    function clearSeries(seriesId) {
      validateSeries(seriesId);
      refresh();
      return write(document.records.filter(function (record) { return record.series_id !== seriesId; }));
    }

    function importText(text, seriesId) {
      const imported = parseDocument(text); // Reject the entire file before touching existing state.
      if (seriesId !== undefined) requireSeries(imported, seriesId);
      refresh();
      const merged = new Map(document.records.map(function (record) { return [key(record), record]; }));
      imported.records.forEach(function (record) {
        const old = merged.get(key(record));
        if (!old || record.completed_at > old.completed_at) merged.set(key(record), record);
      });
      return write(Array.from(merged.values()));
    }

    refresh();
    return {
      snapshot: snapshot, refresh: refresh, toggle: toggle, toggleExercise: toggleExercise, clearSeries: clearSeries, importText: importText,
      exportText: function (seriesId) {
        if (seriesId !== undefined) validateSeries(seriesId);
        refresh();
        const exported = { schema_version: SCHEMA_VERSION, records: document.records.filter(function (record) {
          return seriesId === undefined || record.series_id === seriesId;
        }) };
        return JSON.stringify(exported, null, 2) + '\n';
      },
      rawCorruptText: function () { return corruptRaw; },
    };
  }

  function statusText(state) {
    if (state.compatible) return '已完成（兼容旧版）';
    if (state.completed) return '已完成';
    if (state.outdated) return '内容已更新，建议重新学习（保留历史记录）';
    return '未完成';
  }

  function initialize(doc, win) {
    const roots = Array.from(doc.querySelectorAll('[data-course-progress]'));
    if (!roots.length) return null;
    let storage;
    try { storage = win.localStorage; } catch (_) { storage = null; }
    const store = createStore(storage);
    const configurations = [];
    let actionMessage = '';

    function render() {
      const snapshot = store.snapshot();
      let notice = '学习进度只保存在同一浏览器、同一网站地址下，不上传。清理浏览器数据会丢失进度，可用导出文件备份。';
      if (snapshot.mode === 'session') notice = '浏览器存储不可用：本次勾选仅在当前页面有效，刷新后可能丢失，请导出备份。';
      if (snapshot.mode === 'corrupt') notice = '已保存的进度格式损坏：原数据未被覆盖。本次操作仅在当前页面有效。可导出本系列当前进度，也可导出损坏的原始数据供恢复检查。';
      if (win.location && win.location.protocol === 'file:') notice += ' 本地文件预览的存储行为因浏览器而异，正式网站会按同一域名保存。';
      configurations.forEach(function (config) {
        const summary = summarize(snapshot.records, config.seriesId, config.items.map(function (item) { return item.lesson; }));
        config.root.querySelectorAll('[data-progress-summary]').forEach(function (element) {
          element.textContent = '已完成 ' + summary.completed + ' / ' + summary.total + ' 个单元 · ' + summary.percent + '%';
        });
        config.root.querySelectorAll('progress[data-progress-meter]').forEach(function (element) {
          element.max = 100;
          element.value = summary.percent;
          element.textContent = summary.percent + '%';
        });
        config.root.querySelectorAll('[data-progress-notice]').forEach(function (element) {
          element.textContent = notice + (actionMessage ? ' ' + actionMessage : '');
        });
        config.root.querySelectorAll('[data-progress-export-raw]').forEach(function (element) {
          element.hidden = snapshot.mode !== 'corrupt';
          element.disabled = snapshot.mode !== 'corrupt';
        });
        config.items.forEach(function (item) {
          const state = lessonState(snapshot.records, config.seriesId, item.lesson);
          item.element.querySelectorAll('[data-lesson-status]').forEach(function (element) { element.textContent = statusText(state); });
          item.element.querySelectorAll('[data-course-complete]').forEach(function (element) {
            element.checked = state.completed;
            element.disabled = false;
          });
          const exerciseSummary = summarizeExercises(snapshot.records, config.seriesId, config.exercises.filter(function (exercise) {
            return exercise.spec.lesson_id === item.lesson.lesson_id;
          }).map(function (exercise) { return exercise.spec; }));
          item.element.querySelectorAll('[data-exercise-summary]').forEach(function (element) {
            element.textContent = '已完成 ' + exerciseSummary.completed + ' / ' + exerciseSummary.total + ' 项练习 · 整课完成需另行手动勾选';
          });
        });
        config.exercises.forEach(function (exercise) {
          const state = exerciseState(snapshot.records, config.seriesId, exercise.spec, exercise.spec.exercise_id);
          exercise.element.querySelectorAll('[data-exercise-status]').forEach(function (element) { element.textContent = statusText(state); });
          exercise.element.querySelectorAll('[data-exercise-complete]').forEach(function (element) {
            element.checked = state.completed;
            element.disabled = false;
          });
        });
      });
    }

    function act(operation, success) {
      try { operation(); actionMessage = success || ''; }
      catch (error) { actionMessage = error instanceof ProgressError ? error.message : '操作未完成，请稍后重试或导出备份。'; }
      render();
    }

    function download(text, filename, type) {
      const blob = new win.Blob([text], { type: type });
      const url = win.URL.createObjectURL(blob);
      const link = doc.createElement('a');
      link.href = url;
      link.download = filename;
      doc.body.appendChild(link);
      try { link.click(); } finally {
        link.remove();
        win.setTimeout(function () { win.URL.revokeObjectURL(url); }, 1000);
      }
    }

    roots.forEach(function (root) {
      let config;
      try {
        config = { root: root, seriesId: root.dataset.seriesId, items: Array.from(root.querySelectorAll('[data-course-lesson]')).map(function (element) {
          const versions = (element.dataset.compatibleVersions || '').split(',').map(function (value) { return value.trim(); }).filter(Boolean).sort();
          const lesson = { lesson_id: element.dataset.lessonId, content_version: element.dataset.contentVersion || root.dataset.contentVersion, compatible_versions: versions };
          validLesson(root.dataset.seriesId, lesson);
          return { element: element, lesson: lesson };
        }) };
        if (!config.items.length) throw new ProgressError('本页没有可记录进度的课程单元。');
        summarize([], config.seriesId, config.items.map(function (item) { return item.lesson; }));
        config.exercises = Array.from(root.querySelectorAll('[data-course-exercise]')).map(function (element) {
          const ancestor = element.closest('[data-course-lesson]');
          const parent = config.items.find(function (item) { return item.element === ancestor; });
          const lessonId = element.dataset.lessonId || (parent && parent.lesson.lesson_id);
          const knownLesson = config.items.find(function (item) { return item.lesson.lesson_id === lessonId; });
          if (!knownLesson) throw new ProgressError('练习未关联到当前课程单元。');
          const compatible = element.dataset.compatibleVersions === undefined ? knownLesson.lesson.compatible_versions
            : element.dataset.compatibleVersions.split(',').map(function (value) { return value.trim(); }).filter(Boolean).sort();
          const spec = { lesson_id: lessonId, exercise_id: element.dataset.exerciseId,
            content_version: element.dataset.contentVersion || knownLesson.lesson.content_version,
            compatible_versions: compatible };
          validExercise(config.seriesId, spec, spec.exercise_id);
          return { element: element, spec: spec };
        });
        summarizeExercises([], config.seriesId, config.exercises.map(function (exercise) { return exercise.spec; }));
      } catch (error) {
        root.querySelectorAll('[data-progress-notice]').forEach(function (element) { element.textContent = error.message; });
        return;
      }
      configurations.push(config);
      config.items.forEach(function (item) {
        item.element.querySelectorAll('[data-course-complete]').forEach(function (checkbox) {
          checkbox.addEventListener('change', function () {
            act(function () { store.toggle(config.seriesId, item.lesson, checkbox.checked); });
          });
        });
      });
      config.exercises.forEach(function (exercise) {
        exercise.element.querySelectorAll('[data-exercise-complete]').forEach(function (checkbox) {
          checkbox.addEventListener('change', function () {
            act(function () { store.toggleExercise(config.seriesId, exercise.spec, exercise.spec.exercise_id, checkbox.checked); });
          });
        });
      });
      root.querySelectorAll('[data-progress-clear]').forEach(function (button) {
        button.disabled = false;
        button.addEventListener('click', function () {
          if (win.confirm('清除本系列在此浏览器中的全部进度（包括旧版本记录）？其他系列不受影响。')) {
            act(function () { store.clearSeries(config.seriesId); }, '本系列进度已清除。');
          }
        });
      });
      root.querySelectorAll('[data-progress-export]').forEach(function (button) {
        button.disabled = false;
        button.addEventListener('click', function () {
          act(function () {
            download(store.exportText(config.seriesId), 'vorasio-' + config.seriesId + '-progress-' + new Date().toISOString().slice(0, 10) + '.json', 'application/json');
          }, '已发起本系列进度下载，请检查浏览器下载列表。');
        });
      });
      root.querySelectorAll('[data-progress-export-raw]').forEach(function (button) {
        button.addEventListener('click', function () {
          act(function () {
            const raw = store.rawCorruptText();
            if (raw === null) throw new ProgressError('未发现需要恢复的损坏原始数据。');
            download(raw, 'vorasio-damaged-progress-original.txt', 'text/plain');
          }, '已发起损坏原始数据下载。该文件可能包含全部系列的旧数据，仅供恢复检查，不是可直接导入的备份。');
        });
      });
      const input = root.querySelector('input[type="file"][data-progress-file]');
      root.querySelectorAll('[data-progress-import]').forEach(function (button) {
        button.disabled = !input;
        if (input) button.addEventListener('click', function () { input.click(); });
      });
      if (input) {
        input.disabled = false;
        input.addEventListener('change', async function () {
          const file = input.files && input.files[0];
          input.value = '';
          if (!file) return;
          try {
            if (file.size > MAX_BYTES) throw new ProgressError('进度文件过大，最多支持 1 MB。');
            const text = await file.text();
            const imported = requireSeries(parseDocument(text), config.seriesId);
            if (!win.confirm('将本系列的 ' + imported.records.length + ' 条已完成记录合并到此浏览器？不会删除已有记录，同一单元版本保留较晚的完成时间。旧备份可能恢复你后来取消的完成标记；导入不恢复“未完成”状态。')) return;
            act(function () { store.importText(text, config.seriesId); }, '本系列进度文件已合并。');
          } catch (error) {
            actionMessage = error instanceof ProgressError ? error.message : '无法读取进度文件，未导入任何数据。';
            render();
          }
        });
      }
    });
    win.addEventListener('storage', function (event) {
      if ((event.key === STORAGE_KEY || event.key === null) && (!event.storageArea || event.storageArea === storage)) {
        store.refresh();
        actionMessage = '';
        render();
      }
    });
    render();
    return { store: store, render: render };
  }

  // localStorage has no compare-and-swap transaction: exactly simultaneous writes
  // in multiple tabs can race. Read-latest merge mitigates sequential tab edits;
  // explicit export is the portable backup, not a promise of cross-device sync.
  const api = { STORAGE_KEY: STORAGE_KEY, SCHEMA_VERSION: SCHEMA_VERSION, MAX_RECORDS: MAX_RECORDS, MAX_BYTES: MAX_BYTES, ProgressError: ProgressError,
    validateDocument: validateDocument, parseDocument: parseDocument, requireSeries: requireSeries, lessonState: lessonState,
    exerciseState: exerciseState, summarizeExercises: summarizeExercises, summarize: summarize, createStore: createStore, initialize: initialize };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else {
    global.VorasioCourseProgress = api;
    if (global.document.readyState === 'loading') global.document.addEventListener('DOMContentLoaded', function () { initialize(global.document, global); }, { once: true });
    else initialize(global.document, global);
  }
})(typeof window !== 'undefined' ? window : globalThis);
