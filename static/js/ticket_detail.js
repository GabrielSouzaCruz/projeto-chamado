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

// Controlador global do fetch de DESENHO do chat (GET da lista de comentários).
// Usado para cancelar pedidos de renderização obsoletos quando há muitos envios
// ou eventos Pusher em cadeia — evita a Race Condition entre atualizarChat().
// NUNCA toca no POST do formulário (o envio para a base de dados é sagrado).
let chatFetchController = null;

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
    // funções feedbackCarregando() e restaurarBotao() estão em utils.js

    // 3. ANEXO: validação + preview no chat
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

    // 4b. FIX SCROLL LOCK MOBILE: quando o teclado virtual sobe, o browser tenta
    // rolar a janela para manter o input visível — isso congela o scroll livre das
    // mensagens. No focus: trava a janela no topo (o body está com overflow:hidden,
    // então window.scrollTo(0,0) é inofensivo e impede o "salto") e, após a animação
    // do teclado (~300ms), desce as MENSAGENS para o fim. O layout 100dvh recalcado
    // pelo --vh-real (ajustarAlturaReal) mantém o input visível acima do teclado.
    if (chatInput && chatBox) {
        chatInput.addEventListener("focus", function() {
            window.scrollTo(0, 0);
            setTimeout(function() {
                window.scrollTo(0, 0);
                scrollToBottom(true);
            }, 300);
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

            // Limpeza INSTANTÂNEA do campo: o utilizador vê o envio "já feito"
            // antes mesmo da resposta do servidor (perceção de envio imediato).
            // Se a rede falhar, o texto é restaurado abaixo no catch.
            const textoOriginal = chatInput ? chatInput.value : "";
            this.reset();
            if (chatFile) chatFile.value = "";
            atualizarPreviewChat();
            if (chatInput) chatInput.value = "";

            fetch(this.action, {
                method: "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            })
            .then(response => {
                if (response.ok) {
                    // Atualiza o chat imediatamente (fallback) e também via Pusher,
                    // garantindo que a própria mensagem sempre apareça na tela.
                    window.atualizarChat();
                    scrollToBottom();
                } else {
                    console.error("Erro ao enviar mensagem.", response.status);
                    mostrarNotificacao("Erro ao enviar a mensagem. Tente novamente.", "danger");
                    if (chatInput) chatInput.value = textoOriginal;
                }
            })
            .catch(() => {
                mostrarNotificacao("Erro de rede ao enviar a mensagem.", "danger");
                if (chatInput) chatInput.value = textoOriginal;
            })
            .finally(() => {
                enviando = false;
                restaurarBotao(submitBtn);
            });
        });
    }

    // 7. ATUALIZAR O CHAT SILENCIOSAMENTE E COM ALTA PERFORMANCE
    // Preserva a posição de leitura: só rola ao fim se o usuário JÁ estava no fim.
    // AbortController: cancela APENAS o GET de desenho da tela quando um novo
    // atualizarChat() dispara antes do anterior terminar (Race Condition). O
    // POST do formulário (#form-comentario) NUNCA é tocado por este controlador.
    window.atualizarChat = function() {
        if (!chatBox) return;

        // Puxa APENAS o HTML dos comentários através da nossa nova mini-API
        const urlApi = window.TICKET_CONFIG.urls.comentariosPartial;

        // Estava no fim? (margem de 60px para não saltar com bordas/paddings)
        const estavaNoFim = chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight < 60;

        // Cancela qualquer GET de renderização ainda pendente (obsoleto).
        if (chatFetchController) {
            chatFetchController.abort();
        }
        chatFetchController = new AbortController();

        fetch(urlApi, { signal: chatFetchController.signal })
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
        .catch(error => {
            if (error.name === 'AbortError') return; // cancelado por um GET novo
            console.error("Erro ao atualizar o chat:", error);
        });
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

// ---------------------------------------------------------------------------
// Integração HTMX do chat — código que antes vivia em <script> inline no
// #form-comentario. A CSP do projeto não tem 'unsafe-eval' e o htmx foi
// configurado com allowEval=false, então hx-on é proibido: o comportamento
// (troca condicional, rolagem, polling com aba oculta e reset do form)
// acontece aqui, em JS externo.
// ---------------------------------------------------------------------------

// 1. TROCA CONDICIONAL: o container só é substituído quando a resposta é a
//    parcial real (o 422 de validação vem com o alert e entra acima do form;
//    respostas sem o container não devem destruí-lo). O alvo é resolvido no
//    momento da troca: o polling e o envio podem chegar quase juntos e trocar
//    o nó do container — mirar sempre o nó vivo evita swap em nó desanexado.
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

// 4. Envio bem-sucedido via HTMX → reset no formulário (comentário já está
//    na tela via swap; erros 422 preservam o que o usuário digitou).
//    O alvo é o #form-comentario para não zerar o form a cada polling GET.
document.addEventListener('htmx:afterRequest', function (e) {
    if (e.detail && e.detail.successful && e.target && e.target.id === 'form-comentario') {
        e.target.reset();
    }
});

// 5. GUARDA ANTI-DUPLA GRAVAÇÃO: o form mantém o handler legado (fetch) intacto
//    como fallback, e ele também faz POST para /comentar/. Quem grava agora é o
//    htmx — para não salvar o comentário DUAS vezes (2ª gravação estourava o
//    rate limit/lock do SQLite e o legado restaurava o texto com erro), o fetch
//    legado do envio recebe uma resposta sintética ASSIM QUE o htmx termina:
//    o legado segue cuidando de reset/spinner/atualizarChat, sem gravar de novo.
//    Se o htmx não emitir o envio, a flag nunca sobe e o fetch legado continua
//    real (fallback 100% preservado).
var fetchOriginalLegado = window.fetch;
var envioLegadoPendente = null;

document.addEventListener('htmx:beforeRequest', function (e) {
    if (e.target && e.target.id === 'form-comentario') {
        window.__htmxEnviouComentario = true;
    }
});

document.addEventListener('htmx:afterRequest', function (e) {
    if (!envioLegadoPendente) return;
    if (!e.target || e.target.id !== 'form-comentario') return;
    var pendente = envioLegadoPendente;
    envioLegadoPendente = null;
    var status = (e.detail && e.detail.xhr) ? e.detail.xhr.status : 0;
    if (status === 0) {
        pendente.rejeitar(new TypeError('Failed to fetch'));
    } else {
        pendente.resolver(new Response(JSON.stringify({ status: status >= 200 && status < 400 ? 'success' : 'error' }), {
            status: status,
            headers: { 'Content-Type': 'application/json' }
        }));
    }
});

window.fetch = function (input, init) {
    var url = typeof input === 'string' ? input : (input && input.url) || '';
    var metodo = ((init && init.method) || (input && input.method) || 'GET').toUpperCase();
    if (metodo === 'POST' && window.__htmxEnviouComentario && /\/comentar\/?$/.test(String(url).split('?')[0])) {
        window.__htmxEnviouComentario = false;
        return new Promise(function (resolver, rejeitar) {
            envioLegadoPendente = { resolver: resolver, rejeitar: rejeitar };
        });
    }
    return fetchOriginalLegado.apply(this, arguments);
};
