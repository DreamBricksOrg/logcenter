(() => {
  const apiKey = localStorage.getItem('api_key');
  if (!apiKey) {
    Swal.fire({
      icon: 'warning',
      title: 'Acesso Negado',
      text: 'Faça login primeiro.',
      confirmButtonText: 'Ir para Login',
    }).then(() => (location.href = '/pages/'));
    return;
  }

  const form = document.getElementById('user-form');
  const spinner = document.getElementById('spinner-container');
  const resultEl = document.getElementById('result');
  const backBtn = document.getElementById('clients-back');

  const toggleBtn = document.getElementById('toggle-picker');
  const panelEl = document.getElementById('picker-panel');

  const searchEl = document.getElementById('project-search');
  const listEl = document.getElementById('project-list');
  const chipsEl = document.getElementById('selected-chips');
  const countEl = document.getElementById('project-count');

  const btnSelectVisible = document.getElementById('select-visible');
  const btnClearSelected = document.getElementById('clear-selected');
  const btnLoadMore = document.getElementById('load-more');

  backBtn?.addEventListener('click', () => (location.href = '/pages/clients'));
  panelEl?.addEventListener('click', (e) => {
    e.stopPropagation();
  });

  let projects = []; // {code, name}
  const selected = new Set(); // codes

  // “pagina” de resultados no dropdown
  const PAGE = 30;
  let visibleLimit = PAGE;

  async function fetchJSON(url, opts = {}) {
    const res = await fetch(url, {
      ...opts,
      headers: {
        ...(opts.headers || {}),
        'X-API-Key': apiKey,
      },
    });

    if (res.status === 401) {
      Swal.fire({
        icon: 'error',
        title: 'Sessão Expirada',
        text: 'Por favor, faça login novamente.',
      }).then(() => (location.href = '/pages/'));
      throw new Error('unauthorized');
    }

    if (res.status === 204) return null;

    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.detail || 'Erro na requisição.');
    return data;
  }

  async function loadProjects() {
    try {
      let p;
      try {
        p = await fetchJSON('/projects', { method: 'GET' });
      } catch {
        p = await fetchJSON('/projects/', { method: 'GET' });
      }

      const arr = Array.isArray(p) ? p : p.data || [];
      projects = arr
        .filter((x) => x?.code)
        .map((x) => ({ code: String(x.code), name: String(x.name || x.code) }))
        .sort((a, b) => a.code.localeCompare(b.code, 'pt-BR'));

      visibleLimit = PAGE;
      renderChips();
      renderList();
      updateCount();
    } catch (e) {
      if (String(e.message) !== 'unauthorized') {
        Swal.fire(
          'Erro',
          e.message || 'Não foi possível carregar projetos.',
          'error'
        );
      }
    }
  }

  function normalize(s) {
    return String(s || '')
      .toLowerCase()
      .trim();
  }

  function filteredProjects() {
    const q = normalize(searchEl?.value);
    if (!q) return projects;
    return projects.filter(
      (p) => normalize(p.code).includes(q) || normalize(p.name).includes(q)
    );
  }

  function renderList() {
    if (!listEl) return;

    const filtered = filteredProjects();
    const slice = filtered.slice(0, visibleLimit);

    listEl.innerHTML = '';

    if (!slice.length) {
      listEl.innerHTML =
        '<div style="opacity:.75; padding:8px 0;">Nenhum projeto encontrado.</div>';
      btnLoadMore.disabled = true;
      return;
    }

    slice.forEach((p) => {
      const row = document.createElement('div');
      row.className = 'project-item';

      const isChecked = selected.has(p.code);
      row.innerHTML = `
        <input type="checkbox" class="project-checkbox" data-code="${escapeAttr(p.code)}" ${isChecked ? 'checked' : ''} />
        <div class="project-meta">
          <div class="project-name">${escapeHtml(p.name || p.code)}</div>
          <div class="project-code" title="${escapeAttr(p.code)}">${escapeHtml(p.code)}</div>
        </div>
      `;

      row.querySelector('input')?.addEventListener('change', (e) => {
        const code = e.target.getAttribute('data-code') || '';
        if (!code) return;

        if (e.target.checked) selected.add(code);
        else selected.delete(code);

        renderChips();
        updateCount();
      });

      listEl.appendChild(row);
    });

    // habilita/desabilita “Carregar mais”
    btnLoadMore.disabled = visibleLimit >= filtered.length;
  }

  function renderChips() {
    if (!chipsEl) return;

    const codes = Array.from(selected).sort((a, b) =>
      a.localeCompare(b, 'pt-BR')
    );
    chipsEl.innerHTML = '';

    if (!codes.length) {
      chipsEl.innerHTML = '<div class="hint">Nenhum projeto selecionado.</div>';
      if (toggleBtn) toggleBtn.textContent = 'Selecionar projetos…';
      return;
    }

    if (toggleBtn)
      toggleBtn.textContent = `Projetos selecionados (${codes.length})`;

    const codeToName = new Map(projects.map((p) => [p.code, p.name || p.code]));

    for (const code of codes) {
      const name = codeToName.get(code) || code;

      const chip = document.createElement('span');
      chip.className = 'chip';

      chip.innerHTML = `
      <span class="chip-text" title="${escapeAttr(name)}">${escapeHtml(name)}</span>
      <button type="button" aria-label="Remover" data-code="${escapeAttr(code)}">×</button>
    `;

      chip.querySelector('button')?.addEventListener('click', (e) => {
        const c = e.currentTarget?.getAttribute('data-code') || '';
        if (!c) return;

        selected.delete(c);

        const cb = document.querySelector(
          `.project-checkbox[data-code="${cssEscape(c)}"]`
        );
        if (cb) cb.checked = false;

        renderChips();
        updateCount();
      });

      chipsEl.appendChild(chip);
    }
  }

  function updateCount() {
    if (!countEl) return;
    const filtered = filteredProjects().length;
    const total = projects.length;
    countEl.textContent = `${selected.size} selecionado(s) • ${filtered} encontrados`;
  }

  // retrátil
  toggleBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();

    const open = panelEl.style.display !== 'none';
    panelEl.style.display = open ? 'none' : 'block';

    if (!open) {
      setTimeout(() => searchEl?.focus(), 0);
    }
  });

  document.addEventListener('click', (e) => {
    if (!panelEl) return;

    const box = document.querySelector('.picker-box');
    if (!box) return;

    const clickedInside = box.contains(e.target);
    if (!clickedInside) {
      panelEl.style.display = 'none';
    }
  });

  // busca reseta limite
  searchEl?.addEventListener('input', () => {
    visibleLimit = PAGE;
    renderList();
    updateCount();
  });

  btnLoadMore?.addEventListener('click', () => {
    visibleLimit += PAGE;
    renderList();
  });

  btnSelectVisible?.addEventListener('click', () => {
    const slice = filteredProjects().slice(0, visibleLimit);
    slice.forEach((p) => selected.add(p.code));

    document.querySelectorAll('.project-checkbox').forEach((cb) => {
      cb.checked = true;
    });

    renderChips();
    updateCount();
  });

  btnClearSelected?.addEventListener('click', () => {
    selected.clear();
    document.querySelectorAll('.project-checkbox').forEach((cb) => {
      cb.checked = false;
    });
    renderChips();
    updateCount();
  });

  // submit
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitBtn = form.querySelector('button[type="submit"]');

    spinner.style.display = 'block';
    resultEl.innerHTML = '';
    if (submitBtn) submitBtn.disabled = true;

    const email = (form.elements.namedItem('email')?.value || '').trim();
    const name = (form.elements.namedItem('name')?.value || '').trim();
    const role = (form.elements.namedItem('role')?.value || 'client').trim();
    const password_plain = (
      form.elements.namedItem('password_plain')?.value || ''
    ).trim();

    const extraRaw = (
      form.elements.namedItem('project_codes_extra')?.value || ''
    ).trim();
    const extraCodes = extraRaw
      ? extraRaw
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
      : [];

    const project_codes = Array.from(
      new Set([...Array.from(selected), ...extraCodes])
    );

    if (!email || !name || !password_plain) {
      Swal.fire('Erro', 'Preencha email, nome e senha.', 'error');
      spinner.style.display = 'none';
      if (submitBtn) submitBtn.disabled = false;
      return;
    }
    if (password_plain.length < 8) {
      Swal.fire('Erro', 'A senha deve ter no mínimo 8 caracteres.', 'error');
      spinner.style.display = 'none';
      if (submitBtn) submitBtn.disabled = false;
      return;
    }

    const payload = { email, name, role, password_plain };
    if (project_codes.length) payload.project_codes = project_codes;

    try {
      const created = await fetchJSON('/users/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      resultEl.innerHTML = `
        <div class="result-box">
          <p>✅ Usuário criado com sucesso!</p>
          <p style="margin: 10px 0;">
            <strong>ID:</strong> ${escapeHtml(created._id || '')}<br>
            <strong>Nome:</strong> ${escapeHtml(created.name || '')}<br>
            <strong>Email:</strong> ${escapeHtml(created.email || '')}<br>
            <strong>Role:</strong> ${escapeHtml(created.role || '')}<br>
            <strong>Project Codes:</strong> ${(created.project_codes || []).map(escapeHtml).join(', ') || '(nenhum)'}
          </p>
        </div>
      `;

      Swal.fire({
        icon: 'success',
        title: 'Sucesso!',
        text: 'Usuário criado.',
        timer: 1500,
        showConfirmButton: false,
      });

      form.reset();
      selected.clear();
      visibleLimit = PAGE;
      renderChips();
      renderList();
      updateCount();
      panelEl.style.display = 'none';
    } catch (e2) {
      if (String(e2.message) !== 'unauthorized') {
        Swal.fire(
          'Erro',
          e2.message || 'Não foi possível criar o usuário.',
          'error'
        );
      }
    } finally {
      spinner.style.display = 'none';
      if (submitBtn) submitBtn.disabled = false;
    }
  });

  function escapeHtml(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
  function escapeAttr(s) {
    return escapeHtml(s).replace(/`/g, '&#096;');
  }
  function cssEscape(s) {
    return String(s).replace(/"/g, '\\"');
  }

  loadProjects();
})();
