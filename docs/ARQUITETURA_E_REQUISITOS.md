# Arquitetura, Requisitos e Rastreabilidade — Sistema Ótica Jurado (MVP)

## 1. Contexto e Problema Real (Experiência Prática I)
- **Parceiro Comunitário:** Ótica Jurado (Gestora: Marcia Jurado).
- **Problema Diagnosticado:** Armazenamento manual de fichas de clientes e receitas oftalmológicas em fichários de papel presos por elásticos, gerando lentidão no atendimento de retorno, risco de perda de histórico (dioptrias, tipos de lentes compradas, datas de compra) e retrabalho operacional.
- **Alinhamento ODS:**
  - **ODS 8 (Trabalho Decente e Crescimento Econômico - Meta 8.3):** Modernização tecnológica de microempreendimento local, elevando a produtividade e reduzindo o tempo de busca de fichas.
  - **ODS 10 (Redução das Desigualdades) e ODS 3 (Saúde e Bem-Estar):** Recursos de acessibilidade visual nativos (Modo de Alto Contraste, Ajuste Dinâmico de Fonte `A+`/`A-`, navegação completa por teclado `Tab` e botões com área mínima de 44x44px).

---

## 2. Padrão Arquitetural em 3 Camadas (Experiência Prática II)
O sistema adota a **Arquitetura Monolítica em Camadas (3 Camadas)** para isolar responsabilidades e permitir testes automatizados sem acoplamento com a interface gráfica:

1. **Camada de Apresentação (`src/ui/app_window.py`):**
   - Implementada em `Tkinter` / `ttk`.
   - Contempla as 3 telas rastreáveis do protótipo:
     - **Tela 1:** Login e Autenticação Segura (`RNF01`).
     - **Tela 2:** Cadastro de Clientes e Registro de Receitas/Vendas Ópticas (`RF01`, `RF02`, `RNF02`).
     - **Tela 3:** Consulta Rápida por Nome ou CPF (`RF03`, `RNF03`), Janela Secundária de Detalhes do Histórico e Exportação de Orçamento/Ficha (`RF04`).
2. **Camada de Regras de Negócio (`src/services/auth_service.py` e `src/services/otica_service.py`):**
   - Validação de campos obrigatórios, normalização de CPF e telefone, validação de dioptrias (OD/OE), autenticação com hash criptográfico de senha e geração de relatórios/orçamentos em TXT e CSV.
3. **Camada de Persistência / Acesso a Dados (`src/database/db_manager.py`):**
   - Implementa o padrão DAO com suporte a **MySQL (`PyMySQL`)** e banco relacional embarcado local (`SQLite3` em `data/otica_jurado.db`), utilizando exclusivamente **Consultas Parametrizadas (`Prepared Statements`)**.

---

## 3. Matriz de Rastreabilidade de Requisitos

| Código | Tipo | Descrição | Implementação no Código |
| :--- | :--- | :--- | :--- |
| **RF01** | Funcional (Obrigatório) | Cadastro de clientes (nome, CPF, telefone, data de nascimento, endereço) | `OticaService.cadastrar_cliente()` / `DatabaseManager.inserir_cliente()` |
| **RF02** | Funcional (Obrigatório) | Registro de receitas e vendas ópticas vinculadas ao cliente (OD/OE, tipo de lente ex: *Crizal Acrílica*, armação, valor, data e status) | `OticaService.registrar_receita()` / `DatabaseManager.inserir_receita()` |
| **RF03** | Funcional (Obrigatório) | Consulta rápida de clientes e histórico por Nome ou CPF | `OticaService.buscar_historico_clientes()` / Aba Consulta e Janela Secundária |
| **RF04** | Funcional (Desejável) | Exportação de dados e emissão de ficha/orçamento em CSV e TXT | `OticaService.exportar_relatorio_csv()` e `OticaService.gerar_orcamento_txt()` |
| **RNF01** | Segurança (OWASP A07) | Autenticação segura com hash criptográfico salgado (`bcrypt` / `PBKDF2-HMAC-SHA256`), proibindo texto limpo ou MD5/SHA-1 | `AuthService.gerar_hash_senha()` e `AuthService.verificar_senha()` |
| **RNF02** | Segurança (OWASP A01, A03, A05) | Consultas parametrizadas contra SQL Injection, validação de sessão ativa e ocultação de stack traces | `DatabaseManager` (placeholders `?`/`%s`) e tratamento de exceções na camada de serviço |
| **RNF03** | Desempenho | Carregamento e busca de registros em menos de 2 segundos (< 2000 ms) com índices no banco | Índices `idx_clientes_nome` e `idx_clientes_cpf` + medição em tempo real na UI |
