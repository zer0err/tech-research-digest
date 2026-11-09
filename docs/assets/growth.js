const form = document.querySelector('#project-brief');
const output = document.querySelector('#brief-output');
const status = document.querySelector('#brief-status');
if (form && output && status) {
  form.addEventListener('submit', event => {
    event.preventDefault();
    const fields = [['direction', '项目方向'], ['problem', '希望解决的问题'], ['audience', '用户与场景'], ['resources', '现有条件'], ['outcome', '交付与验收'], ['constraints', '时间与预算']];
    const data = new FormData(form);
    output.value = 'AI 项目需求摘要\n\n' + fields.map(([key, label]) => `${label}：${String(data.get(key) || '').trim() || '待讨论'}`).join('\n\n');
    const source = safeSourcePath();
    if (source) output.value += `\n\n站内来源：${source}`;
    status.textContent = '摘要已在本页生成，尚未发送。';
  });
  document.querySelector('#copy-brief')?.addEventListener('click', async () => {
    if (!output.value) { status.textContent = '请先生成需求摘要。'; return; }
    try {
      await navigator.clipboard.writeText(output.value);
      status.textContent = '已复制。请自行粘贴、检查并发送。';
    } catch {
      output.focus(); output.select();
      status.textContent = '无法自动复制，已选中摘要，请使用设备的复制功能。';
    }
  });
}

function safeSourcePath() {
  const candidate = new URLSearchParams(location.search).get('source') || document.referrer;
  if (!candidate) return '';
  try {
    const source = new URL(candidate, location.origin);
    return source.origin === location.origin ? source.pathname : '';
  } catch { return ''; }
}
// Enable fields only after the preventDefault handler has been installed.
if (form && output && status) {
  const fields = form.querySelector('[data-brief-fields]');
  if (fields) fields.disabled = false;
}
