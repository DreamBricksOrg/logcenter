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

  const pageSize = 9;
  let currentPage = 1;

  let projectCodeToName = new Map(); // code -> name
  let selectedGroup = '__all__';

  const el = {
    spinner: document.getElementById('loading-spinner'),
    container:
      document.getElementById('users-container') ||
      document.getElementById('clients-container') ||
      document.getElementById('users-container'),
    pagination: document.getElementById('pagination'),
    prev: document.getElementById('prev-page-btn'),
    next: document.getElementById('next-page-btn'),
    pageInfo: document.getElementById('page-info'),
    reload: document.getElementById('reload-btn'),
    groupSelect: document.getElementById('group-select'),
    groupSummary: document.getElementById('group-summary'),
    projectsBtn: document.getElementById('projects-btn'),
    clientsBtn: document.getElementById('clients-btn'),
    logoutBtn: document.getElementById('logout-btn'),
    newUserBtn: document.getElementById('new-user-btn'),
  };

  const requiredIds = [
    'loading-spinner',
    'pagination',
    'prev-page-btn',
    'next-page-btn',
    'page-info',
    'reload-btn',
    'group-select',
    'group-summary',
  ];

  el.projectsBtn?.addEventListener(
    'click',
    () => (location.href = '/pages/admin')
  );
  el.clientsBtn?.addEventListener(
    'click',
    () => (location.href = '/pages/clients')
  );
  el.newUserBtn?.addEventListener(
    'click',
    () => (location.href = '/pages/clients/form')
  );

  el.logoutBtn?.addEventListener('click', async () => {
    const r = await Swal.fire({
      title: 'Sair?',
      text: 'Isso vai remover sua sessão local.',
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Logout',
      cancelButtonText: 'Cancelar',
    });
    if (!r.isConfirmed) return;
    localStorage.clear();
    location.href = '/pages/';
  });

  el.prev.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      loadPage();
    }
  });

  el.next.addEventListener('click', () => {
    currentPage++;
    loadPage();
  });

  el.groupSelect.addEventListener('change', () => {
    selectedGroup = el.groupSelect.value;
    currentPage = 1;
    loadPage();
  });

  el.reload.addEventListener('click', () => {
    currentPage = 1;
    loadInitial();
  });

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
    if (!res.ok) {
      const msg = data?.detail || 'Erro na requisição.';
      throw new Error(msg);
    }
    return data;
  }

  function normalizePaged(data) {
    if (Array.isArray(data)) {
      return {
        items: data,
        total: data.length,
        page: 1,
        page_size: data.length,
      };
    }
    if (data && Array.isArray(data.items)) {
      return {
        items: data.items,
        total: Number(data.total ?? data.items.length),
        page: Number(data.page ?? 1),
        page_size: Number(data.page_size ?? data.items.length),
      };
    }
    if (data && Array.isArray(data.data)) {
      return {
        items: data.data,
        total: data.data.length,
        page: 1,
        page_size: data.data.length,
      };
    }
    return { items: [], total: 0, page: 1, page_size: pageSize };
  }

  async function loadProjectsMap() {
    let projects = [];
    try {
      const p = await fetchJSON(`/projects/?&page=1&page_size=1000`, {
        method: 'GET',
      });
      const norm = normalizePaged(p);
      projects = norm.items;
    } catch (e) {
      console.error('Erro ao carregar projetos:', e);
    }

    const map = new Map();
    for (const pr of projects) {
      const code = pr?.code;
      if (code) map.set(code, pr.name || code);
    }
    return map;
  }

  async function loadInitial() {
    el.spinner.style.display = 'block';
    el.container.innerHTML = '';
    el.pagination.hidden = true;

    try {
      projectCodeToName = await loadProjectsMap();

      // Carrega primeira página para:
      // - render
      // - montar o select com base nos grupos vistos
      const first = await fetchJSON(`/users/?page=1&page_size=${pageSize}`, {
        method: 'GET',
      });
      const norm = normalizePaged(first);

      buildGroupSelectFromPage(norm.items, norm.total);
      currentPage = 1;
      renderPage(norm);

      el.reload.textContent = 'Recarregar';
    } catch (e) {
      if (String(e.message) !== 'unauthorized') {
        Swal.fire('Erro', e.message || 'Falha ao carregar usuários.', 'error');
      }
    } finally {
      el.spinner.style.display = 'none';
      el.pagination.hidden = false;
    }
  }

  async function loadPage() {
    el.spinner.style.display = 'block';
    el.container.innerHTML = '';
    el.pagination.hidden = true;

    try {
      const groupParam =
        selectedGroup === '__all__'
          ? ''
          : selectedGroup === '__none__'
            ? '&group=__none__'
            : `&group=${encodeURIComponent(selectedGroup)}`;

      const data = await fetchJSON(
        `/users/?page=${currentPage}&page_size=${pageSize}`,
        { method: 'GET' }
      );
      const norm = normalizePaged(data);

      mergeGroupsFromItems(norm.items);
      const filteredItems = filterUsersByGroup(norm.items, selectedGroup);

      renderCards(filteredItems);
      updatePagination(norm.total);

      updateSummary(norm.total);
    } catch (e) {
      if (String(e.message) !== 'unauthorized') {
        Swal.fire('Erro', e.message || 'Falha ao carregar usuários.', 'error');
      }
    } finally {
      el.spinner.style.display = 'none';
      el.pagination.hidden = false;
    }
  }

  let knownGroups = new Set();

  function buildGroupSelectFromPage(items, totalUsers) {
    knownGroups = new Set();
    let noGroupCount = 0;

    for (const u of items) {
      const arr = Array.isArray(u.project_codes) ? u.project_codes : [];
      if (!arr.length) noGroupCount++;
      for (const c of arr) if (c) knownGroups.add(c);
    }

    renderGroupSelect(totalUsers, noGroupCount);
  }

  function mergeGroupsFromItems(items) {
    let changed = false;
    let noGroupCount = 0;

    for (const u of items) {
      const arr = Array.isArray(u.project_codes) ? u.project_codes : [];
      if (!arr.length) noGroupCount++;
      for (const c of arr) {
        if (c && !knownGroups.has(c)) {
          knownGroups.add(c);
          changed = true;
        }
      }
    }

    if (changed) {
      renderGroupSelect(null, null);
    }
  }

  function renderGroupSelect(totalUsersMaybe, noGroupMaybe) {
    const sorted = Array.from(knownGroups).sort((a, b) =>
      a.localeCompare(b, 'pt-BR')
    );

    const prevValue = selectedGroup;
    el.groupSelect.innerHTML = '';

    const optAll = document.createElement('option');
    optAll.value = '__all__';
    optAll.textContent =
      totalUsersMaybe != null ? `Todos (${totalUsersMaybe})` : 'Todos';
    el.groupSelect.appendChild(optAll);

    const optNone = document.createElement('option');
    optNone.value = '__none__';
    optNone.textContent =
      noGroupMaybe != null ? `(sem grupo) (${noGroupMaybe})` : '(sem grupo)';
    el.groupSelect.appendChild(optNone);

    for (const c of sorted) {
      const name = projectCodeToName.get(c);
      const label = name && name !== c ? `${c} (${name})` : c;
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = label;
      el.groupSelect.appendChild(opt);
    }

    const exists =
      prevValue === '__all__' ||
      prevValue === '__none__' ||
      sorted.includes(prevValue);

    selectedGroup = exists ? prevValue : '__all__';
    el.groupSelect.value = selectedGroup;
  }

  function filterUsersByGroup(users, group) {
    if (group === '__all__') return users;
    if (group === '__none__') {
      return users.filter(
        (u) => !(Array.isArray(u.project_codes) && u.project_codes.length)
      );
    }
    return users.filter(
      (u) => Array.isArray(u.project_codes) && u.project_codes.includes(group)
    );
  }

  function updatePagination(totalItems) {
    const totalPages = Math.max(
      1,
      Math.ceil(Number(totalItems || 0) / pageSize)
    );
    if (currentPage > totalPages) currentPage = totalPages;

    el.pageInfo.textContent = `Página ${currentPage} / ${totalPages}`;
    el.prev.disabled = currentPage === 1;
    el.next.disabled = currentPage >= totalPages;
  }

  function updateSummary(totalItems) {
    const groupLabel =
      selectedGroup === '__all__'
        ? 'Todos'
        : selectedGroup === '__none__'
          ? '(sem grupo)'
          : selectedGroup;

    el.groupSummary.textContent = `${groupLabel} • total ${totalItems} usuário(s) (paginado)`;
  }

  function renderPage(norm) {
    const items = Array.isArray(norm.items) ? norm.items : [];
    const filtered = filterUsersByGroup(items, selectedGroup);
    renderCards(filtered);
    updatePagination(norm.total);
    updateSummary(norm.total);
  }

  function renderCards(users) {
    el.container.innerHTML = '';

    if (!users.length) {
      el.container.innerHTML =
        '<p style="grid-column: 1/-1; text-align:center;">Nenhum usuário encontrado.</p>';
      return;
    }

    for (const user of users) {
      const id = user._id || user.id;
      const codes = Array.isArray(user.project_codes) ? user.project_codes : [];

      const chips = codes.length
        ? codes
            .map((c) => {
              const nm = projectCodeToName.get(c);
              const label = nm && nm !== c ? `${c} (${nm})` : c;
              return `<span style="display:inline-block; padding:4px 8px; border:1px solid rgba(0,0,0,.15); border-radius:999px; margin:4px 6px 0 0; font-size:.85rem;">${escapeHtml(label)}</span>`;
            })
            .join('')
        : `<span style="opacity:.7;">(sem grupo)</span>`;

      const div = document.createElement('div');
      div.className = 'card';
      div.id = `user-${id}`;

      div.innerHTML = `
        <div class="card-header">
          <span class="slug-title">${escapeHtml(user.name || '(sem nome)')}</span>
          <span style="font-size: 0.8rem;">${escapeHtml(user.role || '')}</span>
        </div>

        <div class="card-body">
          <label>
            Nome
            <input type="text" id="name-${id}" value="${escapeAttr(user.name || '')}">
          </label>

          <label>
            Email
            <input type="email" id="email-${id}" value="${escapeAttr(user.email || '')}" disabled>
          </label>

          <label>
            Role
            <select id="role-${id}">
              <option value="client" ${user.role === 'client' ? 'selected' : ''}>client</option>
              <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>admin</option>
            </select>
          </label>

          <label>
            Nova senha (opcional)
            <input type="password" id="pwd-${id}" placeholder="min 8 caracteres">
          </label>

          <label>
            Grupos (separados por vírgula)
            <input type="text" id="codes-${id}" value="${escapeAttr((codes || []).join(', '))}">
          </label>

        </div>

        <div class="card-footer">
          <div class="card-actions">
            <button onclick="window.__lc_updateUser('${escapeJs(id)}')">Salvar</button>
            <button class="btn-delete" onclick="window.__lc_deleteUser('${escapeJs(id)}','${escapeJs(user.email || user.name || id)}')">Excluir</button>
          </div>
          <div class="status" id="status-${id}" style="text-align:center; height:1.2rem;"></div>
        </div>
      `;

      el.container.appendChild(div);
    }
  }

  window.__lc_updateUser = async function (userId) {
    const btn = document.querySelector(
      `#user-${CSS.escape(userId)} button[onclick^="window.__lc_updateUser"]`
    );
    const originalText = btn?.textContent ?? 'Salvar';
    if (btn) {
      btn.textContent = 'Salvando...';
      btn.disabled = true;
    }

    const name = document.getElementById(`name-${userId}`)?.value ?? '';
    const role = document.getElementById(`role-${userId}`)?.value ?? 'client';
    const pwd = document.getElementById(`pwd-${userId}`)?.value ?? '';
    const codesRaw = document.getElementById(`codes-${userId}`)?.value ?? '';

    const project_codes = codesRaw
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    const payload = {};
    if (name.trim()) payload.name = name.trim();
    if (role) payload.role = role;
    payload.project_codes = project_codes;
    if (pwd.trim()) payload.password_plain = pwd.trim();

    try {
      const updated = await fetchJSON(`/users/${encodeURIComponent(userId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const st = document.getElementById(`status-${userId}`);
      if (st) {
        st.textContent = '✔️ Atualizado!';
        setTimeout(() => (st.textContent = ''), 2000);
      }

      await loadPage();
    } catch (e) {
      Swal.fire(
        'Erro',
        e.message || 'Não foi possível atualizar o usuário.',
        'error'
      );
      const st = document.getElementById(`status-${userId}`);
      if (st) st.textContent = '❌ Erro ao atualizar.';
    } finally {
      if (btn) {
        btn.textContent = originalText;
        btn.disabled = false;
      }
    }
  };

  window.__lc_deleteUser = async function (userId, label) {
    const r = await Swal.fire({
      title: 'Tem certeza?',
      text: `Excluir usuário "${label}"?`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6',
      confirmButtonText: 'Sim, excluir!',
      cancelButtonText: 'Cancelar',
    });

    if (!r.isConfirmed) return;

    try {
      await fetchJSON(`/users/${encodeURIComponent(userId)}`, {
        method: 'DELETE',
      });
      Swal.fire('Excluído!', 'O usuário foi removido.', 'success');
      // volta 1 página se você deletou o último item e ficou vazio
      await loadPage();
    } catch (e) {
      Swal.fire(
        'Erro',
        e.message || 'Não foi possível excluir o usuário.',
        'error'
      );
    }
  };

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
  function escapeJs(s) {
    return String(s ?? '')
      .replace(/\\/g, '\\\\')
      .replace(/'/g, "\\'");
  }

  // init
  loadInitial();
})();
