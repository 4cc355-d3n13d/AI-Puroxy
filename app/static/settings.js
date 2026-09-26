/* Страница /settings: список источников и перезапуск на новом адресе. */

const sizeNode = document.getElementById('db-size');
sizeNode.textContent = fmtBytes(Number(sizeNode.dataset.bytes));

/* ---------------------------------------------------------------- источники */

const sources = document.getElementById('sources');

/* Радиокнопка и «удалить» ссылаются на строку по её номеру среди всех строк —
   так сервер сопоставляет их с полями src_url без отдельных id у новых строк. */
function renumberSources() {
  sources.querySelectorAll('.source-row').forEach((row, index) => {
    row.querySelector('input[name="active_source"]').value = String(index);
    row.querySelector('input[name="src_delete"]').value = String(index);
  });
}

/* Готовый base URL для клиента обновляется по мере ввода префикса. */
sources.addEventListener('input', (event) => {
  if (event.target.name !== 'src_prefix') return;
  const row = event.target.closest('.source-row');
  const code = row.querySelector('.source-endpoint');
  const prefix = event.target.value.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
    || event.target.placeholder;
  if (code && !row.classList.contains('is-new')) code.textContent = `${sources.dataset.base}/${prefix}/v1`;
});

document.getElementById('add-source').addEventListener('click', () => {
  const row = document.getElementById('source-template').content.firstElementChild.cloneNode(true);
  sources.appendChild(row);
  renumberSources();
  if (!sources.querySelector('input[name="active_source"]:checked')) {
    row.querySelector('input[name="active_source"]').checked = true;
  }
  row.querySelector('input[name="src_name"]').focus();
});

sources.addEventListener('change', (event) => {
  if (event.target.name !== 'src_delete') return;
  const row = event.target.closest('.source-row');
  row.classList.toggle('is-deleted', event.target.checked);
  // пустую новую строку проще убрать совсем
  if (event.target.checked && row.classList.contains('is-new') && !row.querySelector('input[name="src_url"]').value) {
    row.remove();
    renumberSources();
  }
});

/* ---------------------------------------------------------------- перезапуск */

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/* Ответ другого порта нельзя прочитать (CORS), но no-cors-запрос отличает
   «сервер ответил» от сетевой ошибки — этого достаточно. */
async function reachable(url) {
  try {
    await fetch(url, { mode: 'no-cors', cache: 'no-store' });
    return true;
  } catch (error) {
    return false;
  }
}

async function restart(button) {
  const { host, port } = button.dataset;
  // слушает только localhost — открыть его можно лишь с этой же машины
  const browserHost = host === '127.0.0.1' && !['localhost', '127.0.0.1'].includes(location.hostname)
    ? '127.0.0.1' : location.hostname;
  const target = `${location.protocol}//${browserHost}:${port}/settings`;
  button.disabled = true;
  button.textContent = 'Перезапуск…';
  try {
    const response = await fetch('/_api/restart', { method: 'POST' });
    if (!response.ok) throw new Error((await response.json()).error || response.statusText);
  } catch (error) {
    button.disabled = false;
    button.textContent = 'Перезапустить сейчас';
    document.getElementById('restart-banner').insertAdjacentHTML('beforeend',
      `<div class="small">Не удалось перезапустить: ${esc(error.message)}</div>`);
    return;
  }
  // сначала дожидаемся, что прежний процесс ушёл, иначе на том же порту ответит он
  for (let i = 0; i < 12 && await reachable(target); i += 1) await sleep(250);
  for (let i = 0; i < 90; i += 1) {
    if (await reachable(target)) {
      location.href = target;
      return;
    }
    button.textContent = `Ждём сервис… ${i + 1} с`;
    await sleep(1000);
  }
  button.textContent = 'Сервис не ответил';
  document.getElementById('restart-banner').insertAdjacentHTML('beforeend',
    `<div class="small">Проверьте <code>./service.sh status</code> и журнал <code>./service.sh logs</code>. Новый адрес: <a href="${esc(target)}">${esc(target)}</a></div>`);
}

const restartButton = document.getElementById('restart-btn');
if (restartButton) restartButton.addEventListener('click', () => restart(restartButton));

/* ---------------------------------------------------------------- оформление: предпросмотр */

const brandPreview = {
  name: document.getElementById('preview-name'),
  mark: document.getElementById('preview-mark'),
  logo: document.getElementById('preview-logo'),
  saved: document.getElementById('preview-logo').getAttribute('src'),
};

function renderBrandPreview() {
  const name = document.getElementById('brand-name').value.trim() || 'Monitoring Proxy';
  const mark = document.getElementById('brand-mark').value.replace(/\s+/g, '').slice(0, 3);
  const remove = document.getElementById('logo-remove');
  const hasLogo = !!brandPreview.logo.getAttribute('src') && !(remove && remove.checked && !brandPreview.picked);
  brandPreview.name.textContent = name;
  brandPreview.mark.textContent = mark;
  // та же проверка, что brand.is_emoji на сервере: ни букв, ни цифр, есть пиктограмма
  brandPreview.mark.classList.toggle('is-emoji', !/[\p{L}\p{N}]/u.test(mark) && /\p{Extended_Pictographic}/u.test(mark));
  brandPreview.logo.hidden = !hasLogo;
  brandPreview.mark.hidden = hasLogo || !mark;
}

document.getElementById('brand-name').addEventListener('input', renderBrandPreview);
document.getElementById('brand-mark').addEventListener('input', renderBrandPreview);
if (document.getElementById('logo-remove')) {
  document.getElementById('logo-remove').addEventListener('change', renderBrandPreview);
}
document.getElementById('logo-input').addEventListener('change', (event) => {
  const file = event.target.files[0];
  if (brandPreview.picked) URL.revokeObjectURL(brandPreview.picked);
  brandPreview.picked = file ? URL.createObjectURL(file) : null;
  brandPreview.logo.src = brandPreview.picked || brandPreview.saved || '';
  if (!brandPreview.picked && !brandPreview.saved) brandPreview.logo.removeAttribute('src');
  renderBrandPreview();
});
