document.addEventListener('DOMContentLoaded', function() {
    // Verificação de autenticação
    const apiKey = localStorage.getItem('api_key');
    if (!apiKey) {
        window.location.href = 'login.html';
        return;
    }
    // Logout: limpa armazenamento e volta para login
    const logoutLink = document.getElementById('logout-link');
    logoutLink.addEventListener('click', function(e) {
        e.preventDefault();
        localStorage.clear();
        window.location.href = 'login.html';
    });
    
    // TODO
});
