// Adiciona listener para submissão do formulário de login
document.getElementById('login-form').addEventListener('submit', function(e) {
    e.preventDefault(); // Evita recarregar a página no submit tradicional
    
    // Obtém valores dos campos de entrada
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    // Elemento para exibir mensagens de erro
    const errorMsg = document.getElementById('error-msg');
    errorMsg.textContent = ''; // Limpa mensagens de erro anteriores
    
    // Envia requisição de autenticação para o endpoint /auth/login
    fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // Corpo da requisição em JSON conforme UnifiedLoginRequest
        body: JSON.stringify({ email: email, password: password })
    })
    .then(response => {
        if (response.ok) {
            // Login bem-sucedido (status 200), converte resposta em JSON
            return response.json();
        } else {
            // Login falhou (credenciais incorretas ou erro do servidor)
            return response.json().then(data => {
                // Lança erro com mensagem retornada pela API (se houver) para ser capturado no catch
                throw new Error(data.detail || 'Falha no login. Verifique suas credenciais.');
            });
        }
    })
    .then(data => {
        // Armazena os dados de login no localStorage para uso posterior
        localStorage.setItem('api_key', data.api_key);
        localStorage.setItem('user_id', data.user_id);
        localStorage.setItem('name', data.name);
        localStorage.setItem('role', data.role);
        localStorage.setItem('project_ids', JSON.stringify(data.project_ids));
        localStorage.setItem('project_codes', JSON.stringify(data.project_codes));
        
        // Redireciona o usuário para a página de projetos após login bem-sucedido
        window.location.href = '/pages/admin';
    })
    .catch(error => {
        // Exibe mensagem de erro amigável ao usuário
        errorMsg.textContent = error.message;
    });
});
