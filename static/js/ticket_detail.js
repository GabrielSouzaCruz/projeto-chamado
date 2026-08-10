// Fallback dinâmico de altura: no Android o 100dvh nem sempre reflete a área
// REALMENTE visível (barra de navegação do SO + teclado virtual) e o
// env(safe-area-inset-bottom) retorna 0px. Esta variável CSS --vh-real
// (usada em ticket_detail.css) é atualizada com a altura do Visual Viewport
// sempre que o teclado abre/fecha ou a janela redimensiona.
function ajustarAlturaReal() {
    if (window.visualViewport) {
        document.documentElement.style.setProperty("--vh-real", window.visualViewport.height + "px");
    }
}
if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", ajustarAlturaReal);
    window.visualViewport.addEventListener("scroll", ajustarAlturaReal);
}
ajustarAlturaReal();

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
    let enviando = false;

    // 1. SCROLL SUAVE E INTELIGENTE
    // instant=true é usado no load inicial (sem animação); o resto é smooth.
    function scrollToBottom(instant = false) {
        if (!chatBox) return;
        chatBox.scrollTo({
            top: chatBox.scrollHeight,
            behavior: instant ? "auto" : "smooth",
        });
    }
    scrollToBottom(true);

    // 2. FEEDBACK DE AÇÕES RÁPIDAS (spinner + texto "A processar..." + restauração)
    function feedbackCarregando(btn, texto) {
        if (!btn) return;
        if (!btn.dataset.originalHtml) btn.dataset.originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> ' + (texto || "A processar...");
    }
    function restaurarBotao(btn) {
        if (!btn) return;
        btn.disabled = false;
        btn.removeAttribute("aria-busy");
        if (btn.dataset.originalHtml) btn.innerHTML = btn.dataset.originalHtml;
    }

    // 3. ANEXO: validação + preview no chat
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

    // 4. RESGATE DO CTRL+V: cola imagens direto no campo de texto
    // Cada colagem cria um novo DataTransfer() — nunca acumula colagens anteriores.
    if (chatInput && chatFile) {
        chatInput.addEventListener("paste", function(e) {
            const itens = e.clipboardData && e.clipboardData.items;
            if (!itens) return;

            const dt = new DataTransfer();
            let achouImagem = false;

            for (const item of itens) {
                if (item.kind === "file" && item.type.startsWith("image/")) {
                    e.preventDefault();
                    const arquivo = item.getAsFile();
                    const nome = arquivo.name || "colado.png";
                    const arquivoColado = new File([arquivo], nome, { type: arquivo.type });
                    dt.items.add(arquivoColado);
                    achouImagem = true;
                }
            }

            if (achouImagem) {
                chatFile.files = dt.files;
                atualizarPreviewChat();
            }
        });
    }

    // 5. ATALHO ENTER para enviar a mensagem (com trava anti-double-submit)
    if (chatInput && formComentario) {
        chatInput.addEventListener("keydown", function(e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault(); // impede a quebra de linha
                if (enviando) return;
                formComentario.requestSubmit(); // dispara o handler de submit (AJAX)
            }
        });
    }

    // 6. INTERCEPTAR O ENVIO DO FORMULÁRIO (Fim dos recarregamentos!)
    if (formComentario) {
        formComentario.addEventListener("submit", function(e) {
            e.preventDefault(); // O segredo que impede a página de piscar/recarregar

            // Trava anti-double-submit: Enter frenético não duplica o envio
            if (enviando) return;
            enviando = true;

            const formData = new FormData(this);
            const mensagem = (formData.get("mensagem") || "").trim();
            const temArquivo = chatFile.files && chatFile.files.length > 0;

            // Permite envio só com anexo (Ctrl+V ou seleção) ou com texto
            if (!mensagem && !temArquivo) {
                enviando = false;
                if (chatInput) chatInput.focus();
                mostrarNotificacao("Escreva uma mensagem ou anexe um arquivo.", "danger");
                return;
            }

            const submitBtn = this.querySelector('button[type="submit"]');

            // Desabilita o botão, mostra o estado "A enviar..." e evita cliques duplos
            feedbackCarregando(submitBtn, "A enviar...");

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
                enviando = false;
                restaurarBotao(submitBtn);
            });
        });
    }

    // 7. ATUALIZAR O CHAT SILENCIOSAMENTE E COM ALTA PERFORMANCE
    // Preserva a posição de leitura: só rola ao fim se o usuário JÁ estava no fim.
    window.atualizarChat = function() {
        if (!chatBox) return;

        // Puxa APENAS o HTML dos comentários através da nossa nova mini-API
        const urlApi = window.TICKET_CONFIG.urls.comentariosPartial;

        // Estava no fim? (margem de 60px para não saltar com bordas/paddings)
        const estavaNoFim = chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight < 60;

        fetch(urlApi)
        .then(response => response.text())
        .then(html => {
            // Guarda altura atual para recalcular a posição relativa após o swap
            const alturaAntes = chatBox.scrollHeight;
            chatBox.innerHTML = html;

            if (estavaNoFim) {
                scrollToBottom(); // suave até a última mensagem
            } else {
                // Mantém a âncora de leitura: desloca pela variação de altura
                chatBox.scrollTop += chatBox.scrollHeight - alturaAntes;
            }
        })
        .catch(error => console.error("Erro ao atualizar o chat:", error));
    };

    // 8. AÇÃO RÁPIDA: ALTERAR STATUS (via fetch, sem recarregar)
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

    // 9. AÇÃO RÁPIDA: ASSUMIR CHAMADO (via fetch, sem recarregar)
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

    // 10. MODAIS DE CONFIRMAÇÃO (Cancelar / Apagar) — feedback de carregamento no submit nativo
    document.querySelectorAll("#modalCancelarTicket form, #modalApagarTicket form").forEach(function(form) {
        form.addEventListener("submit", function() {
            feedbackCarregando(this.querySelector('button[type="submit"]'));
            // Não há thrown: o submit nativo navega para a página do servidor.
        });
    });

    // 11. MINI-API: atualiza apenas o badge de status SEM quebrar listeners/tooltips.
    // Em vez de outerHTML (que destrói o nó), troca classe e texto do elemento atual.
    window.atualizarStatusTicket = function() {
        const badgeContainer = document.getElementById("ticket-header-status");
        if (!badgeContainer) return;

        fetch(window.TICKET_CONFIG.urls.statusBadgePartial)
            .then(res => res.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, "text/html");
                const novoBadge = doc.querySelector("#ticket-header-status");
                if (!novoBadge) return;

                // Preserva o elemento e seus listeners; atualiza apenas aparência.
                badgeContainer.className = novoBadge.className;
                badgeContainer.textContent = novoBadge.textContent;
            })
            .catch(err => console.error("Erro ao atualizar status:", err));
    };
});
