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

  let allUsers = [];
  let projectCodeToName = new Map(); // code -> name
  let selectedGroup = '__all__';

  const el = {
    spinner: document.getElementById('loading-spinner'),
    container: document.getElementById('project-container'),
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

  el.prev?.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      render();
    }
  });

  el.next?.addEventListener('click', () => {
    currentPage++;
    render();
  });

  el.groupSelect?.addEventListener('change', () => {
    selectedGroup = el.groupSelect.value;
    currentPage = 1;
    render();
  });

  el.reload?.addEventListener('click', () => {
    currentPage = 1;
    loadAll();
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

  async function loadProjectsMap() {
    let projects = [];
    try {
      const p = await fetchJSON('/projects', { method: 'GET' });
      projects = Array.isArray(p) ? p : p.data || [];
    } catch {
      const p2 = await fetchJSON('/projects/', { method: 'GET' });
      projects = Array.isArray(p2) ? p2 : p2.data || [];
    }

    const map = new Map();
    for (const pr of projects) {
      if (pr?.code) map.set(pr.code, pr.name || pr.code);
    }
    return map;
  }

  async function loadAll() {
    el.spinner.style.display = 'block';
    el.container.innerHTML = '';
    el.pagination.hidden = true;

    try {
      projectCodeToName = await loadProjectsMap();

      const users = await fetchJSON('/users/', { method: 'GET' });
      allUsers = Array.isArray(users) ? users : users.data || [];

      buildGroupSelect(allUsers);
      render();

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

  function buildGroupSelect(users) {
    const codes = new Set();
    let noGroupCount = 0;

    for (const u of users) {
      const arr = Array.isArray(u.project_codes) ? u.project_codes : [];
      if (!arr.length) noGroupCount++;
      for (const c of arr) if (c) codes.add(c);
    }

    const sorted = Array.from(codes).sort((a, b) =>
      a.localeCompare(b, 'pt-BR')
    );
    el.groupSelect.innerHTML = '';

    const optAll = document.createElement('option');
    optAll.value = '__all__';
    optAll.textContent = `Todos (${users.length})`;
    el.groupSelect.appendChild(optAll);

    const optNone = document.createElement('option');
    optNone.value = '__none__';
    optNone.textContent = `(sem grupo) (${noGroupCount})`;
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
      selectedGroup === '__all__' ||
      selectedGroup === '__none__' ||
      sorted.includes(selectedGroup);

    if (!exists) selectedGroup = '__all__';
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

  function render() {
    const filtered = filterUsersByGroup(allUsers, selectedGroup);

    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    if (currentPage > totalPages) currentPage = totalPages;

    const start = (currentPage - 1) * pageSize;
    const pageItems = filtered.slice(start, start + pageSize);

    renderCards(pageItems);
    updatePagination(total, totalPages);

    const groupLabel =
      selectedGroup === '__all__'
        ? 'Todos'
        : selectedGroup === '__none__'
          ? '(sem grupo)'
          : selectedGroup;

    el.groupSummary.textContent = `${groupLabel} • ${total} usuário(s)`;
  }

  function updatePagination(totalItems, totalPages) {
    el.pageInfo.textContent = `Página ${currentPage} / ${totalPages}`;
    el.prev.disabled = currentPage === 1;
    el.next.disabled = currentPage >= totalPages;
  }

  function renderCards(users) {
    el.container.innerHTML = '';

    if (!users.length) {
      el.container.innerHTML =
        '<p style="grid-column: 1/-1; text-align:center;">Nenhum usuário encontrado.</p>';
      return;
    }

    for (const user of users) {
      const id = user._id;
      const createdAt = user.createdAt || user.created_at || Date.now();
      const codes = Array.isArray(user.project_codes) ? user.project_codes : [];

      const codesHtml = codes.length
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
          <span style="font-size: 0.8rem;">${new Date(createdAt).toLocaleDateString()}</span>
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
            Project Codes (separados por vírgula)
            <input type="text" id="codes-${id}" value="${escapeAttr((codes || []).join(', '))}">
          </label>

          <div style="margin-top:10px;">
            <div style="font-size:.85rem; opacity:.7; margin-bottom:6px;">Grupos atuais:</div>
            <div>${codesHtml}</div>
          </div>
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

    const payload = {
      name: name.trim() || null,
      role: role || null,
      project_codes,
    };

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
        setTimeout(() => {
          st.textContent = '';
        }, 2000);
      }

      const idx = allUsers.findIndex((u) => u._id === userId);
      if (idx >= 0) allUsers[idx] = updated;
      buildGroupSelect(allUsers);
      render();
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

      allUsers = allUsers.filter((u) => u._id !== userId);
      buildGroupSelect(allUsers);
      render();

      Swal.fire('Excluído!', 'O usuário foi removido.', 'success');
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

  loadAll();
})();
