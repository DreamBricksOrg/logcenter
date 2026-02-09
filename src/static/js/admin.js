(() => {
  const apiKey = localStorage.getItem('api_key');
  if (!apiKey) {
    Swal.fire({
      icon: 'warning',
      title: 'Acesso Negado',
      text: 'Faça login primeiro.',
      confirmButtonText: 'Ir para Login',
    }).then(() => {
      location.href = '/pages/';
    });
    return;
  }

  // TODO - implement filters later
  const filters = {
    // 'filter-slug': 'code',          // encurtador: slug
    // 'filter-tittle': 'name',        // encurtador: title
    // 'filter-notes': 'notes',        // encurtador: notes
    // 'filter-original': 'extra_1',   // encurtador: original_url
    // 'filter-callback': 'extra_2',   // encurtador: callback_url
    // 'filter-date-from': 'date_from',
    // 'filter-date-to': 'date_to'
  };

  let currentPage = 1;
  const pageSize = 9; // 3x3

  // Controles
  document.getElementById('reload-btn').addEventListener('click', () => {
    currentPage = 1;
    loadProjects(true);
  });

  //   document.getElementById('apply-filters-btn').addEventListener('click', () => {
  //     currentPage = 1;
  //     loadProjects(false);
  //   });

  document.getElementById('new-project-btn').addEventListener('click', () => {
    window.location.href = '/pages/form';
  });

  document.getElementById('projects-btn').addEventListener('click', () => {
    window.location.href = '/pages/admin';
  });

  document.getElementById('clients-btn').addEventListener('click', () => {
    window.location.href = '/pages/clients';
  });

  //   document.getElementById('export-btn').addEventListener('click', () => exportCSV());

  document.getElementById('logout-btn').addEventListener('click', async () => {
    const result = await Swal.fire({
      title: 'Sair?',
      text: 'Isso vai remover sua sessão local.',
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Logout',
      cancelButtonText: 'Cancelar',
    });

    if (!result.isConfirmed) return;

    localStorage.clear();
    location.href = '/pages/';
  });

  document.getElementById('prev-page-btn').addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      loadProjects(false);
    }
  });

  document.getElementById('next-page-btn').addEventListener('click', () => {
    currentPage++;
    loadProjects(false);
  });

  async function loadProjects(showControls) {
    const spinner = document.getElementById('loading-spinner');
    const container = document.getElementById('project-container');
    const pagination = document.getElementById('pagination');

    spinner.style.display = 'block';
    container.innerHTML = '';
    pagination.hidden = true;

    const params = new URLSearchParams();
    params.append('page', String(currentPage));
    params.append('page_size', String(pageSize));

    for (const [id, key] of Object.entries(filters)) {
      const el = document.getElementById(id);
      if (!el) continue;
      const val = el.value;
      if (val) params.append(key, val);
    }

    try {
      const res = await fetch(`/projects?${params}`, {
        headers: { 'X-API-Key': apiKey },
      });

      if (res.status === 401) {
        Swal.fire({
          icon: 'error',
          title: 'Sessão Expirada',
          text: 'Por favor, faça login novamente.',
        }).then(() => (location.href = '/pages/'));
        return;
      }

      const json = await res.json().catch(() => ({}));
      const list = Array.isArray(json) ? json : json.data || [];

      renderProjects(list);
      updatePagination(list.length);

      if (showControls) {
        // document.querySelector('.filter-form').hidden = false;
        // document.getElementById('export-btn').hidden = false;
        document.getElementById('reload-btn').textContent = 'Recarregar';
      }
    } catch (error) {
      Swal.fire('Erro', 'Falha ao carregar projetos.', 'error');
      console.error(error);
    } finally {
      spinner.style.display = 'none';
      pagination.hidden = false;
    }
  }

  function updatePagination(itemsCount) {
    document.getElementById('page-info').textContent = `Página ${currentPage}`;
    document.getElementById('prev-page-btn').disabled = currentPage === 1;
    document.getElementById('next-page-btn').disabled = itemsCount < pageSize;
  }

  function renderProjects(list) {
    const c = document.getElementById('project-container');
    c.innerHTML = '';

    if (!Array.isArray(list) || list.length === 0) {
      c.innerHTML =
        '<p style="grid-column: 1/-1; text-align: center;">Nenhum projeto encontrado.</p>';
      return;
    }

    list.forEach((project) => {
      const id = project.id ?? project._id ?? project.project_id ?? '';
      const code = project.code ?? project.name ?? project.project_code ?? '';
      const createdAt = project.created_at ?? project.createdAt ?? Date.now();

      const div = document.createElement('div');
      div.className = 'card';
      div.id = `project-${id}`;

      div.innerHTML = `
        <div class="card-header">
          <span class="slug-title">${escapeHtml(code || '(sem code)')}</span>
          <span style="font-size: 0.8rem;">${new Date(createdAt).toLocaleDateString()}</span>
        </div>

        <div class="card-body">
          <label>
            Code
            <input type="text" id="code-${id}" value="${escapeAttr(code)}">
          </label>
          <label>
            Nome (opcional)
            <input type="text" id="name-${id}" value="${escapeAttr(project.name || '')}">
          </label>
          <label>
            Notas/Descrição (opcional)
            <input type="text" id="notes-${id}" value="${escapeAttr(project.notes || project.description || '')}">
          </label>
        </div>

        <div class="card-footer">
          <button onclick="window.__lc_showProjectKey('${id}', '${escapeJs(code)}')">🔑 API Key</button>
          <button onclick="window.__lc_regenProjectKey('${id}', '${escapeJs(code)}')">♻️ Regenerar API Key</button>

          <div class="card-actions">
            <button onclick="window.__lc_updateProject('${id}')">Salvar</button>
            <button class="btn-delete" onclick="window.__lc_deleteProject('${id}', '${escapeJs(code)}')">Excluir</button>
          </div>

          <div class="status" id="status-${id}" style="text-align: center; height: 1.2rem;"></div>
        </div>
      `;

      c.appendChild(div);
    });
  }

  async function copyToClipboardAny(text) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (_) {}

    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.top = '-9999px';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();

      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    } catch (_) {}

    return false;
  }

  function selectNodeText(el) {
    if (!el) return;
    const range = document.createRange();
    range.selectNodeContents(el);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  }

  // ---- Ações ----

  window.__lc_updateProject = async function (id) {
    const btn = document.querySelector(
      `#project-${CSS.escape(String(id))} button[onclick^="window.__lc_updateProject"]`
    );
    const originalText = btn?.textContent ?? 'Salvar';
    if (btn) {
      btn.textContent = 'Salvando...';
      btn.disabled = true;
    }

    const params = new URLSearchParams({
      code: document.getElementById(`code-${id}`)?.value ?? '',
      name: document.getElementById(`name-${id}`)?.value ?? '',
      notes: document.getElementById(`notes-${id}`)?.value ?? '',
    });

    try {
      const res = await fetch(`/projects/${encodeURIComponent(id)}?${params}`, {
        method: 'PATCH',
        headers: { 'X-API-Key': apiKey },
      });

      const el = document.getElementById(`status-${id}`);
      if (res.status === 401) {
        Swal.fire({
          icon: 'error',
          title: 'Sessão Expirada',
          text: 'Por favor, faça login novamente.',
        }).then(() => (location.href = '/pages/'));
        return;
      }

      if (res.ok) {
        if (el) {
          el.textContent = '✔️ Atualizado!';
          setTimeout(() => {
            if (el) el.textContent = '';
          }, 2000);
        }
      } else {
        if (el) el.textContent = '❌ Erro ao atualizar.';
        Swal.fire('Erro', 'Não foi possível atualizar o projeto.', 'error');
      }
    } catch (err) {
      Swal.fire('Erro', 'Falha na comunicação.', 'error');
    } finally {
      if (btn) {
        btn.textContent = originalText;
        btn.disabled = false;
      }
    }
  };

  window.__lc_deleteProject = async function (id, code) {
    const result = await Swal.fire({
      title: 'Tem certeza?',
      text: `Excluir o projeto "${code}"? Esta ação não pode ser revertida!`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6',
      confirmButtonText: 'Sim, excluir!',
      cancelButtonText: 'Cancelar',
    });

    if (!result.isConfirmed) return;

    try {
      const res = await fetch(`/projects/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        headers: { 'X-API-Key': apiKey },
      });

      if (res.status === 401) {
        Swal.fire({
          icon: 'error',
          title: 'Sessão Expirada',
          text: 'Por favor, faça login novamente.',
        }).then(() => (location.href = '/pages/'));
        return;
      }

      if (res.ok) {
        document.getElementById(`project-${id}`)?.remove();
        Swal.fire('Excluído!', 'O projeto foi removido.', 'success');
      } else {
        Swal.fire('Erro', 'Não foi possível excluir o projeto.', 'error');
      }
    } catch (err) {
      Swal.fire('Erro', 'Falha na comunicação.', 'error');
    }
  };

  window.__lc_showProjectKey = async function (id, code) {
    Swal.fire({
      title: `API Key: ${code}`,
      html: '<div class="spinner"></div><p>Carregando...</p>',
      showConfirmButton: false,
      width: '700px',
    });

    try {
      const res = await fetch(`/projects/${encodeURIComponent(id)}/apikey`, {
        headers: { 'X-API-Key': apiKey },
      });

      if (res.status === 401) {
        Swal.fire({
          icon: 'error',
          title: 'Sessão Expirada',
          text: 'Por favor, faça login novamente.',
        }).then(() => (location.href = '/pages/'));
        return;
      }

      if (!res.ok) throw new Error('Falha ao buscar API key');

      const json = await res.json().catch(() => ({}));
      const key =
        json.api_key_plain ??
        json.api_key ??
        json.apikey ??
        json.key ??
        json.token ??
        json.data?.api_key ??
        '';

      Swal.update({
        html: key
          ? `
            <p style="margin:0 0 10px;">Copie e guarde:</p>
            <pre id="api-key-pre" style="text-align:left; white-space:pre-wrap; word-break:break-all; background:#f6f6f6; padding:12px; border-radius:6px; margin:0;">${escapeHtml(key)}</pre>
            <div style="margin-top: 12px; display:flex; gap:10px; justify-content:center;">
            <button id="copy-key-btn" style="padding: 8px 16px;">Copiar</button>
            <button id="select-key-btn" style="padding: 8px 16px;">Selecionar</button>
            </div>
        `
          : `<p>Não veio API key na resposta.</p>`,
        showConfirmButton: true,
        confirmButtonText: 'Fechar',
      });

      setTimeout(() => {
        const copyBtn = document.getElementById('copy-key-btn');
        const selectBtn = document.getElementById('select-key-btn');
        const pre = document.getElementById('api-key-pre');

        if (selectBtn && pre) {
          selectBtn.onclick = () => selectNodeText(pre);
        }

        if (copyBtn && key) {
          copyBtn.onclick = async () => {
            const ok = await copyToClipboardAny(key);
            if (ok) {
              Swal.fire({
                toast: true,
                position: 'top-end',
                icon: 'success',
                title: 'Copiado!',
                showConfirmButton: false,
                timer: 1500,
              });
            } else {
              Swal.fire({
                icon: 'warning',
                title: 'Não deu pra copiar automaticamente',
                text: 'Clique em "Selecionar" e copie manualmente.',
              });
            }
          };
        }
      }, 0);
    } catch (err) {
      Swal.fire('Erro', 'Não foi possível carregar a API key.', 'error');
    }
  };

  // Regenera API key
  window.__lc_regenProjectKey = async function (id, code) {
    const result = await Swal.fire({
      title: 'Regenerar API Key?',
      html: `<p>Projeto: <strong>${escapeHtml(code)}</strong></p><p>Isso invalida a chave anterior.</p>`,
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Regenerar',
      cancelButtonText: 'Cancelar',
    });

    if (!result.isConfirmed) return;

    try {
      const res = await fetch(`/projects/${encodeURIComponent(id)}/apikey`, {
        method: 'POST',
        headers: { 'X-API-Key': apiKey },
      });

      if (res.status === 401) {
        Swal.fire({
          icon: 'error',
          title: 'Sessão Expirada',
          text: 'Por favor, faça login novamente.',
        }).then(() => (location.href = '/pages/'));
        return;
      }

      const json = await res.json().catch(() => ({}));

      if (!res.ok) {
        Swal.fire(
          'Erro',
          json.detail || 'Não foi possível regenerar a API key.',
          'error'
        );
        return;
      }

      const key = json.api_key_plain ?? json.api_key ?? json.key ?? '';

      if (!key) {
        Swal.fire(
          'Sucesso',
          'API key regenerada, mas não veio no retorno.',
          'success'
        );
        return;
      }

      Swal.fire({
        icon: 'success',
        title: 'API Key regenerada',
        html: `
        <p style="margin:0 0 10px;">Copie agora (a anterior foi invalidada):</p>
        <pre id="api-key-pre" style="text-align:left; white-space:pre-wrap; word-break:break-all; background:#f6f6f6; padding:12px; border-radius:6px; margin:0;">${escapeHtml(key)}</pre>
        <div style="margin-top: 12px; display:flex; gap:10px; justify-content:center;">
          <button id="copy-key-btn" style="padding: 8px 16px;">Copiar</button>
          <button id="select-key-btn" style="padding: 8px 16px;">Selecionar</button>
        </div>
      `,
        showConfirmButton: true,
        confirmButtonText: 'Fechar',
        didOpen: () => {
          const copyBtn = document.getElementById('copy-key-btn');
          const selectBtn = document.getElementById('select-key-btn');
          const pre = document.getElementById('api-key-pre');

          if (selectBtn && pre) {
            selectBtn.onclick = () => selectNodeText(pre);
          }

          if (copyBtn) {
            copyBtn.onclick = async () => {
              const ok = await copyToClipboardAny(key);
              if (ok) {
                Swal.fire({
                  toast: true,
                  position: 'top-end',
                  icon: 'success',
                  title: 'Copiado!',
                  showConfirmButton: false,
                  timer: 1500,
                });
              } else {
                Swal.fire({
                  icon: 'warning',
                  title: 'Não deu pra copiar automaticamente',
                  text: 'Clique em "Selecionar" e copie manualmente.',
                });
              }
            };
          }
        },
      });
    } catch (e) {
      Swal.fire('Erro', 'Falha na comunicação.', 'error');
    }
  };

  async function exportCSV() {
    // const params = new URLSearchParams();
    // const activeFilters = [];
    // for (const [id, key] of Object.entries(filters)) {
    //     const el = document.getElementById(id);
    //     if (!el) continue;
    //     const val = el.value;
    //     if (val) {
    //     params.append(key, val);
    //     activeFilters.push(`${key}-${val}`);
    //     }
    // }
    // try {
    //     const res = await fetch(`/projects/export?${params}`, {
    //     headers: { 'X-API-Key': apiKey }
    //     });
    //     if (!res.ok) throw new Error('Erro ao exportar');
    //     const blob = await res.blob();
    //     const url = URL.createObjectURL(blob);
    //     const date = new Date().toISOString().slice(0, 10);
    //     const slugPart = activeFilters.length ? activeFilters.join("_") : "all";
    //     const a = document.createElement("a");
    //     a.download = `${slugPart}_projects_${date}.csv`;
    //     a.href = url;
    //     a.click();
    //     URL.revokeObjectURL(url);
    // } catch (err) {
    //     Swal.fire('Erro', 'Não foi possível exportar o CSV.', 'error');
    // }
  }

  // Helpers: evitar quebrar HTML/JS com dados
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

  // Load inicial
  loadProjects(true);
})();
