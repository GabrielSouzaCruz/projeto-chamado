# 🎫 Sistema de Chamados PMM - Machado/MG

Um sistema robusto e moderno de gerenciamento de tickets de suporte técnico, desenvolvido para otimizar o atendimento interno com foco em usabilidade e organização.

---

## ✨ Funcionalidades Principais

### 🛠️ Para Técnicos e Administradores

* **Painel de Controle (Dashboard):** Visão geral em tempo real de todos os chamados abertos, em andamento e resolvidos.
* **Fila de Atendimento:** Gerenciamento centralizado com filtros por categoria e status.
* **Notas Internas Sigilosas:** Possibilidade de adicionar comentários visíveis apenas para a equipe técnica.
* **Gestão de Categorias:** Criação e edição dinâmica de categorias de suporte (Rede, Hardware, Software, etc).

### 👤 Para Solicitantes (Usuários)

* **Abertura Simplificada:** Formulário intuitivo para descrição do problema.
* **Acompanhamento em Tempo Real:** Histórico completo de interações e mudanças de status.
* **Sistema de Anexos Moderno:** Suporte a upload de arquivos e imagens (incluindo colar via `Ctrl+V` diretamente no chat).

---

## 🎨 Interface e Padrões Visuais

O projeto utiliza o framework **Bootstrap 5** com personalizações exclusivas:

* **Prioridades Blindadas:** Cores estritas para níveis de urgência (Crítica: Vermelho, Alta: Amarelo, Normal: Azul, Baixa: Cinza).
* **Design Responsivo:** Adaptado para uso em computadores, tablets e smartphones.
* **Interface de Chat:** Balões de conversa intuitivos que separam mensagens do usuário, do técnico e notas do sistema.

---

## 🚀 Como Executar o Projeto

### Pré-requisitos

* Python 3.10 ou superior
* Pip (gerenciador de pacotes)

### Passos para Instalação

1. **Clone o repositório:**
```bash
git clone https://github.com/gabrielsouzacruz/projeto-chamado.git
cd projeto-chamado

```


2. **Crie um ambiente virtual:**
```bash
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate

```


3. **Instale as dependências:**
```bash
pip install -r requirements.txt

```


4. **Execute as migrações do banco de dados:**
```bash
python manage.py migrate

```


5. **Crie um superusuário (Admin):**
```bash
python manage.py createsuperuser

```


6. **Inicie o servidor de desenvolvimento:**
```bash
python manage.py runserver

```


Acesse em: `http://127.0.0.1:8000`

---

## 📂 Estrutura do Projeto

* `/accounts`: Gerenciamento de usuários, perfis e autenticação.
* `/tickets`: Core do sistema (Modelos de chamado, comentários, categorias e lógicas de status).
* `/templates`: Arquivos HTML organizados por aplicação e parciais.
* `/static`: Arquivos CSS, JavaScript, imagens da prefeitura e sons de notificação.

---

## 📧 Notificações

O sistema está preparado para enviar notificações automáticas via E-mail (HTML e Texto) para:

* Criação de novos chamados.
* Mudanças de status (ex: de Aberto para Em Andamento).
* Novas mensagens e comentários recebidos.

---

**Desenvolvido para a Prefeitura Municipal de Machado.**
