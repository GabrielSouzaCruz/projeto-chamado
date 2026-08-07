// Função global: trata anexos cujo arquivo não existe mais (foi removido pelo
// limpar_anexos ou sumiu do storage). Substitui a miniatura/link quebrado por
// um aviso e IMPEDE que a pessoa abra a imagem novamente.
function anexoIndisponivel(el) {
    const caixa = el.closest("a") || el;
    const aviso = document.createElement("span");
    aviso.className = "d-inline-flex align-items-center gap-1 small fst-italic text-muted";
    aviso.innerHTML = '<i class="fas fa-exclamation-triangle" aria-hidden="true"></i> Anexo removido (arquivo indisponível)';
    caixa.replaceWith(aviso);
}

document.addEventListener("DOMContentLoaded", function() {
    const formComentario = document.getElementById("form-comentario");
    const chatBox = document.getElementById("comentarios-container");

    // 6. SILENCIAR A PRÓXIMA NOTIFICAÇÃO (evita o "eco" ao enviar o próprio comentário)
    let silenciarProximaNotificacao = false;
    window.silenciarProximaNotificacao = false;

    // 7. FEEDBACK DE AÇÕES RÁPIDAS (spinner + texto "A processar..." + restauração)
    function feedbackCarregando(btn, texto) {
        if (!btn) return;
        if (!btn.dataset.originalHtml) btn.dataset.originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> ' + (texto || "A processar...");
    }
    function restaurarBotao(btn) {
        if (!btn) return;
        btn.disabled = false;
        if (btn.dataset.originalHtml) btn.innerHTML = btn.dataset.originalHtml;
    }

    // Mantém o scroll no final quando a página carrega
    function scrollToBottom() {
        if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
    }
    scrollToBottom();

    // 0. ANEXO: validação + preview no chat
    const chatFile = document.getElementById("chat-file");
    const chatInput = document.getElementById("chat-input");
    const fileNameBtn = document.getElementById("chat-file-name");
    const previewBox = document.getElementById("chat-anexo-preview");
    const previewThumb = document.getElementById("chat-anexo-thumb");
    const previewNome = document.getElementById("chat-anexo-nome");
    const previewTamanho = document.getElementById("chat-anexo-tamanho");
    const previewRemover = document.getElementById("chat-anexo-remover");
    const EXTENSOES_OK = ["png", "jpg", "jpeg", "gif", "webp", "bmp", "pdf"];
    const TAMANHO_MAX = 2 * 1024 * 1024;

    function anexoClienteValido(arquivo) {
        if (!arquivo) return false;
        const ext = (arquivo.name.split(".").pop() || "").toLowerCase();
        if (!EXTENSOES_OK.includes(ext)) {
            mostrarNotificacao("Formato não permitido. Use apenas imagens (JPG, PNG, GIF, WebP, BMP) ou PDF.", "danger");
            return false;
        }
        if (arquivo.size > TAMANHO_MAX) {
            mostrarNotificacao("Arquivo muito grande. O limite é de 2 MB.", "danger");
            return false;
        }
        return true;
    }

    function atualizarPreviewChat() {
        const arquivo = chatFile.files && chatFile.files[0];
        if (!arquivo) {
            if (previewBox) previewBox.classList.add("d-none");
            if (fileNameBtn) fileNameBtn.innerHTML = '<i class="fas fa-file me-1" aria-hidden="true"></i>';
            return;
        }
        if (!anexoClienteValido(arquivo)) {
            chatFile.value = "";
            if (previewBox) previewBox.classList.add("d-none");
            if (fileNameBtn) fileNameBtn.innerHTML = '<i class="fas fa-file me-1" aria-hidden="true"></i>';
            return;
        }
        const nome = arquivo.name;
        const ext = nome.split(".").pop().toLowerCase();
        const kb = (arquivo.size / 1024).toFixed(1) + " KB";
        if (fileNameBtn) fileNameBtn.innerHTML = '<i class="fas fa-file-pdf me-1 text-danger" aria-hidden="true"></i> ' + nome;
        if (previewNome) previewNome.textContent = nome;
        if (previewTamanho) previewTamanho.textContent = kb;
        if (previewBox) previewBox.classList.remove("d-none");
        if (previewThumb) {
            previewThumb.innerHTML = "";
            if (ext === "pdf") {
                previewThumb.innerHTML = '<i class="fas fa-file-pdf text-danger" aria-hidden="true"></i>';
            } else {
                const reader = new FileReader();
                const img = document.createElement("img");
                img.style.width = "100%";
                img.style.height = "100%";
                img.style.objectFit = "cover";
                img.alt = "Pré-visualização";
                reader.onload = function(e) { img.src = e.target.result; };
                reader.readAsDataURL(arquivo);
                previewThumb.appendChild(img);
            }
        }
    }

    if (chatFile && fileNameBtn && previewBox) {
        chatFile.addEventListener("change", atualizarPreviewChat);
        fileNameBtn.addEventListener("click", function() { chatFile.click(); });
        if (previewRemover) previewRemover.addEventListener("click", function() {
            chatFile.value = "";
            atualizarPreviewChat();
            if (chatInput) chatInput.focus();
        });
    }

    // 0.1 RESGATE DO CTRL+V: cola imagens direto no campo de texto
    if (chatInput && chatFile) {
        chatInput.addEventListener("paste", function(e) {
            const itens = e.clipboardData && e.clipboardData.items;
            if (!itens) return;

            for (const item of itens) {
                if (item.kind === "file" && item.type.startsWith("image/")) {
                    e.preventDefault();
                    const arquivo = item.getAsFile();
                    const nome = arquivo.name || "colado.png";
                    const arquivoColado = new File([arquivo], nome, { type: arquivo.type });

                    const dt = new DataTransfer();
                    if (chatFile.files && chatFile.files[0]) dt.items.add(chatFile.files[0]);
                    dt.items.add(arquivoColado);
                    chatFile.files = dt.files;

                    atualizarPreviewChat();
                    break;
                }
            }
        });
    }

    // 0.2 ATALHO ENTER para enviar a mensagem
    if (chatInput && formComentario) {
        chatInput.addEventListener("keydown", function(e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault(); // impede a quebra de linha
                formComentario.requestSubmit(); // dispara o handler de submit (AJAX)
            }
        });
    }

    // 1. INTERCEPTAR O ENVIO DO FORMULÁRIO (Fim dos recarregamentos!)
    if (formComentario) {
        formComentario.addEventListener("submit", function(e) {
            e.preventDefault(); // O segredo que impede a página de piscar/recarregar

            const formData = new FormData(this);
            const mensagem = (formData.get("mensagem") || "").trim();
            const temArquivo = chatFile.files && chatFile.files.length > 0;

            // Permite envio só com anexo (Ctrl+V ou seleção) ou com texto
            if (!mensagem && !temArquivo) {
                if (chatInput) chatInput.focus();
                mostrarNotificacao("Escreva uma mensagem ou anexe um arquivo.", "danger");
                return;
            }

            const submitBtn = this.querySelector('button[type="submit"]');

            // Desabilita o botão, mostra o estado "A enviar..." e evita cliques duplos
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span> A enviar...';
            }

            fetch(this.action, {
                method: "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            })
            .then(response => {
                if (response.ok) {
                    this.reset(); // Limpa a caixa de texto
                    if (chatFile) chatFile.value = "";
                    atualizarPreviewChat();
                    if (chatInput) chatInput.value = "";
                    // Silencia a notificação do próprio envio (o Pusher devolve o eco)
                    silenciarProximaNotificacao = true;
                    window.silenciarProximaNotificacao = true;
                    // Atualiza o chat imediatamente (fallback) e também via Pusher,
                    // garantindo que a própria mensagem sempre apareça na tela.
                    window.atualizarChat();
                    scrollToBottom();
                } else {
                    console.error("Erro ao enviar mensagem.", response.status);
                    mostrarNotificacao("Erro ao enviar a mensagem. Tente novamente.", "danger");
                }
            })
            .catch(() => {
                mostrarNotificacao("Erro de rede ao enviar a mensagem.", "danger");
            })
            .finally(() => {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = "Enviar";
                }
            });
        });
    }

    // 2. ATUALIZAR O CHAT SILENCIOSAMENTE E COM ALTA PERFORMANCE
    window.atualizarChat = function() {
        if (!chatBox) return;

        // Puxa APENAS o HTML dos comentários através da nossa nova mini-API
        const urlApi = window.TICKET_CONFIG.urls.comentariosPartial;

        fetch(urlApi)
        .then(response => response.text())
        .then(html => {
            // Como a API já devolve só os comentários, é só injetar direto!
            chatBox.innerHTML = html;

            // Rola automaticamente para a última mensagem
            scrollToBottom();
        })
        .catch(error => console.error("Erro ao atualizar o chat:", error));
    };

    // 3. AÇÃO RÁPIDA: ALTERAR STATUS (via fetch, sem recarregar)
    const formStatus = document.getElementById("form-status");
    if (formStatus) {
        formStatus.addEventListener("submit", function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const submitBtn = this.querySelector('button[type="submit"]');
            feedbackCarregando(submitBtn, "A processar...");

            fetch(this.action, {
                method: "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    window.atualizarStatusTicket(); // Puxa o badge novo via mini-API
                    mostrarNotificacao("Status atualizado com sucesso.", "success");
                } else {
                    mostrarNotificacao(data.mensagem || "Erro ao alterar o status.", "danger");
                    console.error("Erro ao alterar status:", data.mensagem || "");
                }
            })
            .catch(err => {
                mostrarNotificacao("Erro de rede ao atualizar o status.", "danger");
                console.error("Erro ao alterar status:", err);
            })
            .finally(() => restaurarBotao(submitBtn));
        });
    }

    // 4. AÇÃO RÁPIDA: ASSUMIR CHAMADO (via fetch, sem recarregar)
    const formAssumir = document.getElementById("form-assumir");
    if (formAssumir) {
        formAssumir.addEventListener("submit", function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const submitBtn = this.querySelector('button[type="submit"]');
            feedbackCarregando(submitBtn, "A processar...");

            fetch(this.action, {
                method: "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Remove o botão de assumir (o chamado já tem dono) e atualiza o badge
                    formAssumir.remove();
                    window.atualizarStatusTicket();
                    mostrarNotificacao("Chamado assumido com sucesso.", "success");
                } else {
                    mostrarNotificacao(data.mensagem || "Erro ao assumir o chamado.", "danger");
                    console.error("Erro ao assumir chamado:", data.mensagem || "");
                }
            })
            .catch(err => {
                mostrarNotificacao("Erro de rede ao assumir o chamado.", "danger");
                console.error("Erro ao assumir chamado:", err);
            })
            .finally(() => {
                // Se o botão ainda estiver na página (ex: erro), restaura-o
                restaurarBotao(submitBtn);
            });
        });
    }

    // 5. MODAIS DE CONFIRMAÇÃO (Cancelar / Apagar) — feedback de carregamento no submit nativo
    document.querySelectorAll("#modalCancelarTicket form, #modalApagarTicket form").forEach(function(form) {
        form.addEventListener("submit", function() {
            feedbackCarregando(this.querySelector('button[type="submit"]'));
            // Não há thrown: o submit nativo navega para a página do servidor.
        });
    });

    // 6. MINI-API: atualiza apenas o badge de status (HTML-over-the-wire)
    window.atualizarStatusTicket = function() {
        const badgeContainer = document.getElementById("ticket-header-status");
        if (!badgeContainer) return;

        fetch(window.TICKET_CONFIG.urls.statusBadgePartial)
            .then(res => res.text())
            .then(html => {
                badgeContainer.outerHTML = html;
            })
            .catch(err => console.error("Erro ao atualizar status:", err));
    };
});
