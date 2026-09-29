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

    // 2. ANEXO: validação + preview no chat
    const chatFile = document.getElementById("chat-file");
    const chatInput = document.getElementById("chat-input");
    const fileNameBtn = document.getElementById("chat-file-name");
    const previewBox = document.getElementById("chat-anexo-preview");
    const previewThumb = document.getElementById("chat-anexo-thumb");
    const previewNome = document.getElementById("chat-anexo-nome");
    const previewTamanho = document.getElementById("chat-anexo-tamanho");
    const previewRemover = document.getElementById("chat-anexo-remover");

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

    // 3. RESGATE DO CTRL+V: cola imagens direto no campo de texto
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

    // 4. FIX SCROLL LOCK MOBILE: quando o teclado virtual sobe, o browser tenta
    // rolar a janela para manter o input visível — isso congela o scroll livre das
    // mensagens. No focus: trava a janela no topo (o body está com overflow:hidden,
    // então window.scrollTo(0,0) é inofensivo e impede o "salto") e, após a animação
    // do teclado (~300ms), desce as MENSAGENS para o fim.
    if (chatInput && chatBox) {
        chatInput.addEventListener("focus", function() {
            window.scrollTo(0, 0);
            setTimeout(function() {
                window.scrollTo(0, 0);
                scrollToBottom(true);
            }, 300);
        });
    }

    // 5. ATALHO ENTER para enviar a mensagem via HTMX
    if (chatInput && formComentario) {
        chatInput.addEventListener("keydown", function(e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault(); // impede a quebra de linha
                formComentario.requestSubmit(); // dispara o hx-post do HTMX
            }
        });
    }

    // 5b. Submit handler para prevenir reload e desabilitar botão
    // (HTMX fará o POST via hx-post, mas precisamos evitar o reload nativo)
    if (formComentario) {
        formComentario.addEventListener("submit", function(e) {
            e.preventDefault(); // HTMX vai interceptar, mas prevenimos o fallback
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) feedbackCarregando(submitBtn, "A enviar...");
            // Limpa o arquivo e preview imediatamente (percepção de envio)
            if (chatFile) chatFile.value = "";
            if (atualizarPreviewChat) atualizarPreviewChat();
        });
    }

    // 6. AÇÃO RÁPIDA: ALTERAR STATUS (via fetch, sem recarregar)
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
                    window.atualizarStatusTicket();
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

    // 7. AÇÃO RÁPIDA: ASSUMIR CHAMADO (via fetch, sem recarregar)
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
                restaurarBotao(submitBtn);
            });
        });
    }

    // 8. MODAIS DE CONFIRMAÇÃO (Cancelar / Apagar) — feedback de carregamento no submit nativo
    document.querySelectorAll("#modalCancelarTicket form, #modalApagarTicket form").forEach(function(form) {
        form.addEventListener("submit", function() {
            feedbackCarregando(this.querySelector('button[type="submit"]'));
        });
    });

    // 9. MINI-API: atualiza apenas o badge de status SEM quebrar listeners/tooltips.
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

                badgeContainer.className = novoBadge.className;
                badgeContainer.textContent = novoBadge.textContent;
            })
            .catch(err => console.error("Erro ao atualizar status:", err));
    };
});

// ---------------------------------------------------------------------------
// Integração HTMX do chat — listeners para swap condicional, scroll,
// polling pausado com aba oculta, e reset automático do formulário.
// ---------------------------------------------------------------------------

// 1. TROCA CONDICIONAL: o container só é substituído quando a resposta é a
//    parcial real. O alvo é resolvido no momento da troca para evitar swap
//    em nó desanexado.
document.addEventListener('htmx:beforeSwap', function (e) {
    var d = e.detail;
    if (!d || !d.target || d.target.id !== 'comentarios-container') return;
    var atual = document.getElementById('comentarios-container');
    if (!atual) { d.shouldSwap = false; return; }
    d.target = atual;
    d.shouldSwap = (d.serverResponse || '').indexOf('comentarios-container') !== -1;
    if (d.shouldSwap) {
        document.querySelectorAll('[data-erro-comentario]').forEach(function (el) { el.remove(); });
    }
});

// 2. Após a troca, o container novo rola até a última mensagem.
document.addEventListener('htmx:afterSwap', function (e) {
    var alvo = e.target;
    if (!alvo || !alvo.closest || !alvo.closest('#comentarios-container')) return;
    var el = document.getElementById('comentarios-container');
    if (!el) return;
    if (el.scrollTo) { el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' }); }
    else { el.scrollTop = el.scrollHeight; }
});

// 3. Polling do chat não roda com a aba oculta — substitui o antigo filtro
//    [document.visibilityState=='visible'] do hx-trigger (que exigia eval).
//    htmx:beforeRequest é cancelável: cancela antes do send (sem rede).
document.addEventListener('htmx:beforeRequest', function (e) {
    var alvo = e.target;
    if (document.hidden && alvo && alvo.id === 'comentarios-container') {
        e.preventDefault();
    }
});

// 4. Envio bem-sucedido via HTMX → reset no formulário e restaura botão
//    (comentário já está na tela via swap; erros 422 preservam o que o usuário digitou).
document.addEventListener('htmx:afterRequest', function (e) {
    if (e.target && e.target.id === 'form-comentario') {
        const submitBtn = e.target.querySelector('button[type="submit"]');
        if (submitBtn && e.detail && e.detail.successful) {
            e.target.reset();
            restaurarBotao(submitBtn);
        } else if (submitBtn) {
            // Mesmo em erro, restaura o botão para o usuário poder tentar novamente
            restaurarBotao(submitBtn);
        }
    }
});
