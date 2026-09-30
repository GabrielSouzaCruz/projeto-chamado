// Atalho Enter para enviar comentário via HTMX
document.addEventListener("DOMContentLoaded", function() {
    const chatInput = document.getElementById("chat-input");
    const formComentario = document.getElementById("form-comentario");

    if (chatInput && formComentario) {
        chatInput.addEventListener("keydown", function(e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                formComentario.requestSubmit();
            }
        });
    }

    // Mobile: scroll quando teclado abre
    const chatBox = document.getElementById("comentarios-container");
    if (chatInput && chatBox) {
        chatInput.addEventListener("focus", function() {
            window.scrollTo(0, 0);
            setTimeout(function() {
                window.scrollTo(0, 0);
                chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: 'auto' });
            }, 300);
        });
    }
});

// HTMX listeners para o chat
// 1. Swap condicional: só substitui se resposta tem container
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

// 2. Após swap, rola até fim
document.addEventListener('htmx:afterSwap', function (e) {
    var alvo = e.target;
    if (!alvo || !alvo.closest || !alvo.closest('#comentarios-container')) return;
    var el = document.getElementById('comentarios-container');
    if (!el) return;
    if (el.scrollTo) { el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' }); }
    else { el.scrollTop = el.scrollHeight; }
});

// 3. Polling pausado com aba oculta
document.addEventListener('htmx:beforeRequest', function (e) {
    var alvo = e.target;
    if (document.hidden && alvo && alvo.id === 'comentarios-container') {
        e.preventDefault();
        return;
    }
    if (alvo && alvo.id === 'form-comentario') {
        var btn = alvo.querySelector('button.chat-send');
        if (btn) {
            btn.setAttribute('aria-busy', 'true');
            var txt = btn.querySelector('.spinner-text');
            if (txt) txt.textContent = 'A enviar';
        }
    }
});

// 4. Reset form após sucesso + restaura botão
document.addEventListener('htmx:afterRequest', function (e) {
    if (e.target && e.target.id === 'form-comentario') {
        var btn = e.target.querySelector('button.chat-send');
        if (btn) {
            btn.removeAttribute('aria-busy');
            var txt = btn.querySelector('.spinner-text');
            if (txt) txt.textContent = 'Enviar';
        }
        if (e.detail && e.detail.successful) {
            e.target.reset();
            const chatFile = document.getElementById('chat-file');
            if (chatFile) chatFile.dispatchEvent(new Event('change'));
        }
    }
});
