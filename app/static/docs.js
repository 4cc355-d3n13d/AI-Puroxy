/* Страница /docs: кнопки копирования у блоков кода и подсветка активного пункта оглавления. */

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.docs-body pre').forEach((pre) => {
    const wrap = document.createElement('div');
    wrap.className = 'code-wrap';
    pre.parentNode.insertBefore(wrap, pre);
    wrap.appendChild(pre);

    const button = document.createElement('button');
    button.className = 'copy-btn';
    button.textContent = 'копировать';
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(pre.innerText);
        button.textContent = 'скопировано';
      } catch (error) {
        button.textContent = 'не вышло';
      }
      setTimeout(() => { button.textContent = 'копировать'; }, 1500);
    });
    wrap.appendChild(button);
  });

  const links = [...document.querySelectorAll('.docs-toc a')];
  const headings = links
    .map((link) => document.getElementById(decodeURIComponent(link.getAttribute('href').slice(1))))
    .filter(Boolean);
  if (!headings.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      links.forEach((link) => link.classList.remove('is-active'));
      const active = links.find((link) => decodeURIComponent(link.getAttribute('href').slice(1)) === entry.target.id);
      if (active) active.classList.add('is-active');
    });
  }, { rootMargin: '-60px 0px -75% 0px' });
  headings.forEach((heading) => observer.observe(heading));
});
