// =============================================================
// UTILS — Funções utilitárias compartilhadas entre templates.
// Importado por base.html (carrega em TODAS as páginas).
// =============================================================

// ---- Validação de anexos (imagens + PDF) ----
const ANEXO_EXTENSOES_OK = ["png", "jpg", "jpeg", "gif", "webp", "bmp", "pdf"];
const ANEXO_TAMANHO_MAX = 2 * 1024 * 1024; // 2 MB

function anexoClienteValido(arquivo) {
    if (!arquivo) return false;
    const ext = (arquivo.name.split(".").pop() || "").toLowerCase();
    if (!ANEXO_EXTENSOES_OK.includes(ext)) {
        const msg = "Formato não permitido. Use apenas imagens (JPG, PNG, GIF, WebP, BMP) ou PDF.";
        if (typeof mostrarNotificacao === "function") mostrarNotificacao(msg, "danger");
        else alert(msg);
        return false;
    }
    if (arquivo.size > ANEXO_TAMANHO_MAX) {
        const msg = "Arquivo muito grande. O limite é de 2 MB.";
        if (typeof mostrarNotificacao === "function") mostrarNotificacao(msg, "danger");
        else alert(msg);
        return false;
    }
    return true;
}

// ---- Feedback de botões (spinner + texto + restauração) ----
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
