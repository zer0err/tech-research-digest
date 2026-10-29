/* Local course enhancements. Reading never requires JavaScript or a model API. */
(() => {
  'use strict';
  document.querySelectorAll('[data-copy-code]').forEach(button => {
    button.disabled = false;
    button.addEventListener('click', async () => {
      const figure = button.closest('.code-example');
      const code = figure.querySelector('code');
      const message = figure.querySelector('.copy-status');
      try {
        await navigator.clipboard.writeText(code.textContent);
        message.textContent = '已复制';
      } catch {
        const selection = window.getSelection();
        if (selection) {
          const range = document.createRange();
          range.selectNodeContents(code);
          selection.removeAllRanges();
          selection.addRange(range);
          message.textContent = '无法自动复制。已选中代码，请按 Ctrl+C（Mac 为 ⌘C）复制。';
        } else {
          message.textContent = '无法自动复制或选中文本。请手动选择内容，再按 Ctrl+C（Mac 为 ⌘C）复制。';
        }
      }
    });
  });
})();
