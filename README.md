# 👓 Sistema MVP — Ótica Jurado

Repositório oficial do MVP de gestão de clientes, receitas oftalmológicas e vendas desenvolvido para a **Ótica Jurado** (Parceira Comunitária: **Marcia Jurado**), substituindo o controle manual em fichários de papel por uma aplicação desktop segura, rápida e acessível.

---

## 🛠️ Tecnologias e Arquitetura (3 Camadas)

- **Linguagem:** Python 3.12+
- **Camada de Apresentação (`/src/ui`):** Tkinter / `ttk` (3 telas rastreáveis + Modo de Alto Contraste + Ajuste Dinâmico de Fonte `A+`/`A-`).
- **Camada de Regras de Negócio (`/src/services`):** Validação de dados cadastrais e ópticos (dioptrias OD/OE, adição, DNP, lentes), geração de fichas/orçamentos (`TXT`) e exportação (`CSV`).
- **Camada de Acesso a Dados (`/src/database`):** Padrão DAO com **Consultas Parametrizadas (`Prepared Statements`)** contra *SQL Injection*, suportando **MySQL (`PyMySQL`)** e banco relacional embarcado local (`SQLite3` em `data/otica_jurado.db`).
- **Segurança (OWASP Top 10):**
  - `RNF01 (OWASP A07:2021)`: Senhas armazenadas exclusivamente com hash criptográfico salgado (`bcrypt` / `PBKDF2-HMAC-SHA256`).
  - `RNF02 (OWASP A01 / A03 / A05)`: Controle de sessão ativa, *Prepared Statements* e mensagens amigáveis sem expor *stack traces*.
- **Desempenho (`RNF03`):** Índices em `clientes(nome)` e `clientes(cpf)` garantindo consultas em menos de **2 segundos (< 2000 ms)**.
- **Alinhamento ODS:** **ODS 8** (Trabalho Decente e Crescimento Econômico), **ODS 10** (Redução das Desigualdades) e **ODS 3** (Saúde e Bem-Estar).

---

## 📂 Estrutura do Projeto

```text
├── .github/workflows/ci.yml        # Pipeline de Integração Contínua (GitHub Actions)
├── docs/
│   ├── ARQUITETURA_E_REQUISITOS.md # Matriz de rastreabilidade (RF01-RF04, RNF01-RNF03, OWASP, ODS)
│   └── schema_mysql.sql            # Script DDL de criação das tabelas e índices no MySQL
├── src/
│   ├── main.py                     # Ponto de entrada da aplicação Desktop
│   ├── database/db_manager.py      # Camada DAO parametrizada e carga inicial de demonstração
│   ├── services/auth_service.py    # Autenticação segura e controle de sessão (RNF01)
│   ├── services/otica_service.py   # Regras de negócio, validações e relatórios (RF01-RF04)
│   └── ui/app_window.py            # Interface gráfica Tkinter (Login, Cadastro, Consulta e Acessibilidade)
├── tests/
│   └── test_otica.py               # 10 testes automatizados unitários e de integração
├── app.py                          # Atalho de execução na raiz
├── test_otica.py                   # Atalho de execução dos testes na raiz
└── requirements.txt                # Dependências do projeto
```

---

## 🚀 Como Executar o Projeto

1. **Executar a aplicação Desktop:**
   ```bash
   python app.py
   ```
   *(ou `python src/main.py`)*
   - **Credenciais padrão de demonstração:**
     - **Usuário:** `gerente`
     - **Senha:** `123456`

2. **Executar a suíte de testes automatizados (10 testes):**
   ```bash
   python -m unittest test_otica.py -v
   ```
