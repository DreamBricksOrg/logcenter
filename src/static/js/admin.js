document.addEventListener('DOMContentLoaded', function() {
    // Verifica se o usuário está autenticado (api_key presente)
    const apiKey = localStorage.getItem('api_key');
    if (!apiKey) {
        // Se não há API key, redireciona para a página de login
        window.location.href = 'login.html';
        return;
    }
    
    // Elemento para exibir mensagens de erro ou aviso
    const errorMsg = document.getElementById('error-msg');
    
    // Configura o botão de Logout para limpar dados e redirecionar
    const logoutLink = document.getElementById('logout-link');
    logoutLink.addEventListener('click', function(e) {
        e.preventDefault();
        localStorage.clear();
        window.location.href = 'login.html';
    });
    
    // Busca a lista de projetos do usuário via API (GET /projects/)
    fetch('/projects/', {
        headers: { 'X-API-Key': apiKey }
    })
    .then(response => {
        if (response.ok) {
            return response.json(); // converte resposta em lista de projetos (JSON)
        } else if (response.status === 401) {
            // Se não autorizado (API key inválida/expirada), faz logout e volta ao login
            localStorage.clear();
            window.location.href = 'login.html';
            throw new Error('');  // interrompe execução do restante
        } else {
            throw new Error('Falha ao carregar projetos.');
        }
    })
    .then(projects => {
        // `projects` é esperado ser uma lista de objetos de projeto
        const tbody = document.querySelector('#projects-table tbody');
        tbody.innerHTML = ''; // garante que a tabela esteja vazia antes de inserir
        
        // Itera sobre cada projeto retornado para criar a linha na tabela
        projects.forEach(proj => {
            // Cria elementos de célula (td) para ID, nome (código) e ações
            const row = document.createElement('tr');
            
            const idCell = document.createElement('td');
            idCell.textContent = proj.id;
            
            const nameCell = document.createElement('td');
            // Assume que o objeto do projeto possui propriedade 'code' ou 'name'
            nameCell.textContent = proj.code || proj.name || proj.project_code;
            
            const actionsCell = document.createElement('td');
            
            // Botão Editar – permite renomear o projeto
            const editBtn = document.createElement('button');
            editBtn.textContent = 'Editar';
            editBtn.addEventListener('click', () => {
                const novoNome = prompt('Novo nome do projeto:', nameCell.textContent);
                if (novoNome) {
                    // Envia requisição PATCH para atualizar o nome/código do projeto
                    fetch(`/projects/${proj.id}`, {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-API-Key': apiKey
                        },
                        body: JSON.stringify({ code: novoNome })
                    })
                    .then(response => {
                        if (response.ok) {
                            // Atualiza visualmente o nome do projeto na tabela
                            nameCell.textContent = novoNome;
                            proj.code = novoNome;
                        } else {
                            // Lê mensagem de erro da resposta (se disponível) e lança para ser exibida
                            return response.json().then(data => {
                                throw new Error(data.detail || 'Erro ao editar projeto.');
                            });
                        }
                    })
                    .catch(err => {
                        errorMsg.textContent = err.message;
                    });
                }
            });
            
            // Botão Excluir – remove o projeto
            const deleteBtn = document.createElement('button');
            deleteBtn.textContent = 'Excluir';
            deleteBtn.addEventListener('click', () => {
                // Pede confirmação antes de excluir
                if (confirm(`Deseja excluir o projeto "${nameCell.textContent}"?`)) {
                    fetch(`/projects/${proj.id}`, {
                        method: 'DELETE',
                        headers: { 'X-API-Key': apiKey }
                    })
                    .then(response => {
                        if (response.ok) {
                            // Remove a linha da tabela no front-end
                            row.remove();
                        } else {
                            return response.json().then(data => {
                                throw new Error(data.detail || 'Erro ao excluir projeto.');
                            });
                        }
                    })
                    .catch(err => {
                        errorMsg.textContent = err.message;
                    });
                }
            });
            
            // Botão Regenerar API Key – obtém uma nova API key para o projeto
            const regenBtn = document.createElement('button');
            regenBtn.textContent = 'Regenerar API Key';
            regenBtn.addEventListener('click', () => {
                // Confirmação antes de regenerar (ação irreversível)
                if (confirm(`Deseja regenerar a API Key do projeto "${nameCell.textContent}"?`)) {
                    fetch(`/projects/${proj.id}/apikey`, {
                        method: 'POST',
                        headers: { 'X-API-Key': apiKey }
                    })
                    .then(response => {
                        if (response.ok) {
                            alert('Nova API key gerada com sucesso.'); 
                            // Opcional: Poderíamos atualizar algo na UI se a chave fosse exibida.
                        } else {
                            return response.json().then(data => {
                                throw new Error(data.detail || 'Erro ao regenerar API key.');
                            });
                        }
                    })
                    .catch(err => {
                        errorMsg.textContent = err.message;
                    });
                }
            });
            
            // Adiciona os botões na célula de ações (com pequenos espaçamentos)
            actionsCell.appendChild(editBtn);
            actionsCell.appendChild(document.createTextNode(' '));
            actionsCell.appendChild(deleteBtn);
            actionsCell.appendChild(document.createTextNode(' '));
            actionsCell.appendChild(regenBtn);
            
            // Monta a linha completa e anexa ao corpo da tabela
            row.appendChild(idCell);
            row.appendChild(nameCell);
            row.appendChild(actionsCell);
            tbody.appendChild(row);
        });
    })
    .catch(err => {
        // Exibe erro geral de carregamento de projetos (se não já tratado acima)
        if (err.message) {
            errorMsg.textContent = err.message;
        }
    });
    
    // Formulário de criação de novo projeto
    const newProjectForm = document.getElementById('new-project-form');
    newProjectForm.addEventListener('submit', function(e) {
        e.preventDefault();
        errorMsg.textContent = ''; // limpa mensagem anterior
        
        const codeInput = document.getElementById('new-project-code');
        const novoProjetoNome = codeInput.value.trim();
        if (!novoProjetoNome) {
            errorMsg.textContent = 'O nome do projeto não pode ser vazio.';
            return;
        }
        // Envia requisição POST para criar um novo projeto
        fetch('/projects/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey
            },
            body: JSON.stringify({ code: novoProjetoNome })
        })
        .then(response => {
            if (response.ok) {
                return response.json(); // novo projeto criado
            } else {
                return response.json().then(data => {
                    throw new Error(data.detail || 'Erro ao criar projeto.');
                });
            }
        })
        .then(newProj => {
            // Adiciona o novo projeto criado na tabela de projetos
            const tbody = document.querySelector('#projects-table tbody');
            const row = document.createElement('tr');
            
            const idCell = document.createElement('td');
            idCell.textContent = newProj.id;
            const nameCell = document.createElement('td');
            nameCell.textContent = newProj.code || newProj.name || newProj.project_code || novoProjetoNome;
            const actionsCell = document.createElement('td');
            
            // Cria botões de ação para o novo projeto (similar aos anteriores)
            const editBtnNew = document.createElement('button');
            editBtnNew.textContent = 'Editar';
            editBtnNew.addEventListener('click', () => {
                const novoNome = prompt('Novo nome do projeto:', nameCell.textContent);
                if (novoNome) {
                    fetch(`/projects/${newProj.id}`, {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-API-Key': apiKey
                        },
                        body: JSON.stringify({ code: novoNome })
                    })
                    .then(response => {
                        if (response.ok) {
                            nameCell.textContent = novoNome;
                            newProj.code = novoNome;
                        } else {
                            return response.json().then(data => {
                                throw new Error(data.detail || 'Erro ao editar projeto.');
                            });
                        }
                    })
                    .catch(err => {
                        errorMsg.textContent = err.message;
                    });
                }
            });
            
            const deleteBtnNew = document.createElement('button');
            deleteBtnNew.textContent = 'Excluir';
            deleteBtnNew.addEventListener('click', () => {
                if (confirm(`Deseja excluir o projeto "${nameCell.textContent}"?`)) {
                    fetch(`/projects/${newProj.id}`, {
                        method: 'DELETE',
                        headers: { 'X-API-Key': apiKey }
                    })
                    .then(response => {
                        if (response.ok) {
                            row.remove();
                        } else {
                            return response.json().then(data => {
                                throw new Error(data.detail || 'Erro ao excluir projeto.');
                            });
                        }
                    })
                    .catch(err => {
                        errorMsg.textContent = err.message;
                    });
                }
            });
            
            const regenBtnNew = document.createElement('button');
            regenBtnNew.textContent = 'Regenerar API Key';
            regenBtnNew.addEventListener('click', () => {
                if (confirm(`Deseja regenerar a API Key do projeto "${nameCell.textContent}"?`)) {
                    fetch(`/projects/${newProj.id}/apikey`, {
                        method: 'POST',
                        headers: { 'X-API-Key': apiKey }
                    })
                    .then(response => {
                        if (response.ok) {
                            alert('Nova API key gerada com sucesso.');
                        } else {
                            return response.json().then(data => {
                                throw new Error(data.detail || 'Erro ao regenerar API key.');
                            });
                        }
                    })
                    .catch(err => {
                        errorMsg.textContent = err.message;
                    });
                }
            });
            
            // Anexa os botões na célula de ações do novo projeto
            actionsCell.appendChild(editBtnNew);
            actionsCell.appendChild(document.createTextNode(' '));
            actionsCell.appendChild(deleteBtnNew);
            actionsCell.appendChild(document.createTextNode(' '));
            actionsCell.appendChild(regenBtnNew);
            
            // Monta a nova linha e adiciona na tabela
            row.appendChild(idCell);
            row.appendChild(nameCell);
            row.appendChild(actionsCell);
            tbody.appendChild(row);
            
            // Limpa o campo de entrada do formulário
            codeInput.value = '';
        })
        .catch(err => {
            errorMsg.textContent = err.message;
        });
    });
});
