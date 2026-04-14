export function renderMarkdown(container, markdown) {
  container.innerHTML = '';
  const lines = (markdown || '').split(/\r?\n/);
  let listEl = null;
  let listType = '';
  let codeBlock = null;

  const closeList = () => {
    listEl = null;
    listType = '';
  };

  const appendText = (tag, text, className) => {
    const el = document.createElement(tag);
    el.textContent = text;
    if (className) el.className = className;
    container.appendChild(el);
    return el;
  };

  lines.forEach(rawLine => {
    const line = rawLine.trimEnd();

    if (line.trim().startsWith('```')) {
      closeList();
      if (codeBlock) {
        codeBlock = null;
      } else {
        codeBlock = document.createElement('pre');
        codeBlock.className = 'my-4 p-4 bg-slate-900 rounded-xl border border-slate-700 text-sm text-slate-300 whitespace-pre-wrap overflow-x-auto';
        container.appendChild(codeBlock);
      }
      return;
    }

    if (codeBlock) {
      codeBlock.textContent += `${line}\n`;
      return;
    }

    if (!line.trim()) {
      closeList();
      const spacer = document.createElement('div');
      spacer.className = 'h-3';
      container.appendChild(spacer);
      return;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      const classes = {
        1: 'text-2xl font-black text-white mt-2 mb-4',
        2: 'text-xl font-bold text-white mt-6 mb-3',
        3: 'text-base font-bold text-indigo-300 mt-5 mb-2',
      };
      appendText(`h${level}`, heading[2], classes[level]);
      return;
    }

    const unordered = line.match(/^[-*]\s+(.+)$/);
    const ordered = line.match(/^\d+[.)]\s+(.+)$/);
    if (unordered || ordered) {
      const nextType = unordered ? 'ul' : 'ol';
      if (!listEl || listType !== nextType) {
        closeList();
        listEl = document.createElement(nextType);
        listType = nextType;
        listEl.className = nextType === 'ul'
          ? 'list-disc pl-6 my-2 space-y-1 text-slate-200'
          : 'list-decimal pl-6 my-2 space-y-1 text-slate-200';
        container.appendChild(listEl);
      }
      const li = document.createElement('li');
      li.textContent = (unordered || ordered)[1];
      listEl.appendChild(li);
      return;
    }

    closeList();
    appendText('p', line, 'my-2 text-slate-200 whitespace-pre-wrap');
  });

  if (!container.childNodes.length) {
    appendText('p', '요약 내용이 비어 있습니다.', 'text-slate-400');
  }
}
