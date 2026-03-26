(() => {
  const apiKey = localStorage.getItem('api_key');
  if (!apiKey) {
    Swal.fire({
      icon: 'warning',
      title: 'Acesso Negado',
      text: 'Faça login primeiro.',
      confirmButtonText: 'Ir para Login'
    }).then(() => {
      location.href = '/pages/';
    });
    return;
  }

  const backBtn = document.getElementById('admin-back');
  const form = document.getElementById('project-form');
  const spinner = document.getElementById('spinner-container');
  const resultEl = document.getElementById('result');

  if (!backBtn || !form || !spinner || !resultEl) {
    console.error('Form DOM mismatch:', {
      backBtn: !!backBtn,
      form: !!form,
      spinner: !!spinner,
      resultEl: !!resultEl,
    });
    return;
  }

  backBtn.addEventListener('click', () => {
    window.location.href = '/pages/admin';
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitBtn = form.querySelector('button[type="submit"]');
    spinner.style.display = 'block';
    resultEl.innerHTML = '';
    if (submitBtn) submitBtn.disabled = true;

    const name = (form.elements.namedItem('name')?.value || '').trim();
    const code = (form.elements.namedItem('code')?.value || '').trim();
    const description = (form.elements.namedItem('description')?.value || '').trim();
    const api_key_plain = (form.elements.namedItem('api_key_plain')?.value || '').trim();
    const status = (form.elements.namedItem('status')?.value || 'active').trim();
    const configRaw = (form.elements.namedItem('config')?.value || '').trim();

    const codeRe = /^[a-z0-9\-_.]+$/;
    if (!codeRe.test(code)) {
      Swal.fire({
        icon: 'error',
        title: 'Code inválido',
        text: 'Use apenas letras minúsculas, números, hífen (-), underscore (_) e ponto (.)'
      });
      spinner.style.display = 'none';
      if (submitBtn) submitBtn.disabled = false;
      return;
    }

    let config = null;
    if (configRaw) {
      try {
        config = JSON.parse(configRaw);
      } catch {
        Swal.fire({
          icon: 'error',
          title: 'Config inválido',
          text: 'O campo Config precisa ser um JSON válido.'
        });
        spinner.style.display = 'none';
        if (submitBtn) submitBtn.disabled = false;
        return;
      }
    }

    const payload = { name, code, status };
    if (description) payload.description = description;
    if (api_key_plain) payload.api_key_plain = api_key_plain;
    if (config) payload.config = config;

    try {
      const response = await fetch('/projects/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify(payload)
      });

      if (response.status === 401) {
        Swal.fire({
          icon: 'error',
          title: 'Sessão Expirada',
          text: 'Por favor, faça login novamente.'
        }).then(() => location.href = '/pages/');
        return;
      }

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        Swal.fire({
          icon: 'error',
          title: 'Erro ao criar projeto',
          text: err.detail || 'Verifique os dados e tente novamente.'
        });
        return;
      }

      const result = await response.json();

      resultEl.innerHTML = `
        <div class="result-box">
          <p>✅ Projeto criado com sucesso!</p>
          <p style="margin: 10px 0;">
            <strong>ID:</strong> ${escapeHtml(result._id || '')}<br>
            <strong>Nome:</strong> ${escapeHtml(result.name || '')}<br>
            <strong>Code:</strong> ${escapeHtml(result.code || '')}<br>
            <strong>Status:</strong> ${escapeHtml(result.status || '')}<br>
            <strong>Has API Key:</strong> ${String(!!result.has_api_key)}
          </p>
          <p style="font-size: 0.9rem; color:#666;">
            createdAt: ${escapeHtml(result.createdAt || '')}
          </p>
        </div>
      `;

      Swal.fire({
        icon: 'success',
        title: 'Sucesso!',
        text: 'Projeto criado.',
        timer: 1500,
        showConfirmButton: false
      });

      form.reset();
    } catch {
      Swal.fire({
        icon: 'error',
        title: 'Erro de Conexão',
        text: 'Não foi possível contatar o servidor.'
      });
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
})();
