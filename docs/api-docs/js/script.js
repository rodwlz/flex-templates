/**
 * Copy-to-clipboard helper for code blocks.
 *
 * Used by the copy buttons rendered above every <pre><code>...</code></pre>
 * snippet on the API documentation pages. The button's structure is:
 *
 *   <div style="position: relative;">
 *     <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
 *     <pre><code class="language-...">...</code></pre>
 *   </div>
 */
function copyToClipboard(button) {
  const code = button.nextElementSibling.querySelector('code');
  if (!code) {
    console.error('copyToClipboard: no <code> element found next to button');
    return;
  }
  const text = code.textContent;

  navigator.clipboard.writeText(text).then(() => {
    const originalText = button.textContent;
    button.textContent = 'Copied!';
    button.classList.add('copied');

    setTimeout(() => {
      button.textContent = originalText;
      button.classList.remove('copied');
    }, 2000);
  }).catch(err => {
    console.error('Failed to copy:', err);
  });
}
