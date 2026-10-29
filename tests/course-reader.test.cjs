const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../docs/assets/course-reader.js'), 'utf8');

function fixture(options = {}) {
  const code = { textContent: '<script>literal text</script>\nprint("中文")\n' };
  const message = { textContent: '' };
  const figure = { querySelector(selector) { return selector === 'code' ? code : message; } };
  const button = { disabled: true, handlers: {}, closest() { return figure; }, addEventListener(type, callback) { this.handlers[type] = callback; } };
  const selection = { removeAllRanges() { this.removed = true; }, addRange(range) { this.range = range; } };
  const copied = [];
  const clipboard = options.missingClipboard ? undefined : { async writeText(text) { if (options.rejectCopy) throw new Error('permission denied'); copied.push(text); } };
  const document = {
    querySelectorAll() { return [button]; },
    createRange() { return { selectNodeContents(node) { this.node = node; } }; },
  };
  vm.runInNewContext(source, { document, navigator: { clipboard }, window: { getSelection() { return options.noSelection ? null : selection; } } });
  return { code, message, button, selection, copied, click: () => button.handlers.click() };
}

test('copy is opt-in and copies literal code text without parsing HTML or making network requests', async () => {
  const f = fixture();
  assert.equal(f.button.disabled, false);
  assert.deepEqual(f.copied, []);
  await f.click();
  assert.deepEqual(f.copied, [f.code.textContent]);
  assert.equal(f.message.textContent, '已复制');
});

for (const options of [{ missingClipboard: true }, { rejectCopy: true }]) {
  test('unavailable or denied clipboard falls back to selecting exactly the code', async () => {
    const f = fixture(options);
    await f.click();
    assert.deepEqual(f.copied, []);
    assert.equal(f.selection.removed, true);
    assert.equal(f.selection.range.node, f.code);
    assert.match(f.message.textContent, /无法自动复制/);
    assert.match(f.message.textContent, /Ctrl\+C/);
  });
}

test('clipboard failure with unavailable selection still gives a manual-copy message without throwing', async () => {
  const f = fixture({ missingClipboard: true, noSelection: true });
  await f.click();
  assert.match(f.message.textContent, /无法自动复制/);
  assert.doesNotMatch(f.message.textContent, /已选中代码/);
});
