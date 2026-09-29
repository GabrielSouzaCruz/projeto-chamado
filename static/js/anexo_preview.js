// Função global: trata anexos cujo arquivo não existe mais
function anexoIndisponivel(el) {
    const caixa = el.closest("a") || el;
    const aviso = document.createElement("span");
    aviso.className = "d-inline-flex align-items-center gap-1 small fst-italic text-muted";
    aviso.innerHTML = '<i class="fas fa-exclamation-triangle" aria-hidden="true"></i> Anexo removido (arquivo indisponível)';
    caixa.replaceWith(aviso);
}

// Preview de anexo no formulário de comentário
document.addEventListener("DOMContentLoaded", function() {
    const chatFile = document.getElementById("chat-file");
    const chatInput = document.getElementById("chat-input");
    const fileNameBtn = document.getElementById("chat-file-name");
    const previewBox = document.getElementById("chat-anexo-preview");
    const previewThumb = document.getElementById("chat-anexo-thumb");
    const previewNome = document.getElementById("chat-anexo-nome");
    const previewTamanho = document.getElementById("chat-anexo-tamanho");
    const previewRemover = document.getElementById("chat-anexo-remover");

    if (!chatFile) return;

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

    if (fileNameBtn && previewBox) {
        chatFile.addEventListener("change", atualizarPreviewChat);
        fileNameBtn.addEventListener("click", function() { chatFile.click(); });
        if (previewRemover) previewRemover.addEventListener("click", function() {
            chatFile.value = "";
            atualizarPreviewChat();
            if (chatInput) chatInput.focus();
        });
    }

    // Ctrl+V: cola imagens direto no campo
    if (chatInput) {
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
});
