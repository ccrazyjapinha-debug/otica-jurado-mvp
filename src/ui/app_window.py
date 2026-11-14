"""
Camada de Apresentação (GUI em Tkinter) - Sistema de Gestão Ótica Jurado (MVP).

Materializa a rastreabilidade definida nas Experiências Práticas I, II e III:
- Tela 1: Menu Inicial e Autenticação Segura (RNF01) com botões >= 44px e foco visível.
- Tela 2: Cadastro de Clientes e Receitas/Vendas Ópticas (RF01, RF02, RNF02).
- Tela 3: Consulta Rápida de Histórico por Nome/CPF (< 2s - RF03, RNF03) +
  Janela Secundária de Detalhes do Cliente e Emissão de Orçamento/Ficha (RF04).
- Acessibilidade (ODS 8, ODS 10 e ODS 3): Alternador de Modo de Alto Contraste
  e Ajuste Dinâmico de Tamanho de Fonte (A+ / A-), navegação por teclado (Tab/Enter).
"""

from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, Optional


class OticaAppWindow:
    """Janela principal do Sistema de Gestão - Ótica Jurado."""

    # Paletas de cores (Modo Padrão vs. Modo Alto Contraste - ODS 10 / Acessibilidade)
    TEMA_PADRAO = {
        "bg_principal": "#f4f6f9",
        "bg_card": "#ffffff",
        "bg_header": "#0d47a1",
        "fg_header": "#ffffff",
        "fg_titulo": "#0d47a1",
        "fg_texto": "#212529",
        "fg_subtexto": "#495057",
        "bg_input": "#ffffff",
        "fg_input": "#212529",
        "btn_primario_bg": "#0d6efd",
        "btn_primario_fg": "#ffffff",
        "btn_sucesso_bg": "#198754",
        "btn_sucesso_fg": "#ffffff",
        "btn_secundario_bg": "#495057",
        "btn_secundario_fg": "#ffffff",
        "btn_alerta_bg": "#dc3545",
        "btn_alerta_fg": "#ffffff",
        "btn_contraste_bg": "#212529",
        "btn_contraste_fg": "#ffffff",
        "borda_foco": "#0d6efd",
        "status_ok": "#198754",
    }

    TEMA_ALTO_CONTRASTE = {
        "bg_principal": "#000000",
        "bg_card": "#121212",
        "bg_header": "#000000",
        "fg_header": "#ffff00",
        "fg_titulo": "#ffff00",
        "fg_texto": "#ffffff",
        "fg_subtexto": "#ffff00",
        "bg_input": "#000000",
        "fg_input": "#ffff00",
        "btn_primario_bg": "#ffff00",
        "btn_primario_fg": "#000000",
        "btn_sucesso_bg": "#00ff66",
        "btn_sucesso_fg": "#000000",
        "btn_secundario_bg": "#333333",
        "btn_secundario_fg": "#ffffff",
        "btn_alerta_bg": "#ff4444",
        "btn_alerta_fg": "#000000",
        "btn_contraste_bg": "#ffff00",
        "btn_contraste_fg": "#000000",
        "borda_foco": "#ffff00",
        "status_ok": "#00ff66",
    }

    def __init__(self, root: tk.Tk, auth_service, otica_service) -> None:
        self.root = root
        self.auth = auth_service
        self.service = otica_service

        self.alto_contraste = False
        self.escala_fonte = 0  # -1, 0, +1, +2 (Ajuste dinâmico de fonte)
        self.tema = self.TEMA_PADRAO

        self.root.title("Sistema de Gestão - Ótica Jurado (MVP v1.0)")
        self.root.geometry("1040x700")
        self.root.minsize(920, 620)

        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        # Container mestre
        self.header_frame: Optional[tk.Frame] = None
        self.body_frame: Optional[tk.Frame] = None
        self.status_bar: Optional[tk.Label] = None

        self._construir_barra_superior()
        self.body_frame = tk.Frame(self.root, bg=self.tema["bg_principal"])
        self.body_frame.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(
            value="✔ Sistema pronto | Banco de Dados Local Conectado | Acessibilidade: Navegação via Tab e Alto Contraste disponíveis"
        )
        self.status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            padx=12,
            pady=6,
            font=self._fonte(9, "bold"),
            bg="#e9ecef",
            fg="#212529",
        )
        self.status_bar.pack(fill="x", side="bottom")

        self._aplicar_estilos_ttk()
        self.mostrar_tela_login()

    def _fonte(self, tamanho_base: int, peso: str = "normal") -> tuple:
        """Calcula a fonte dinamicamente conforme a escala de acessibilidade."""
        tamanho = max(8, tamanho_base + self.escala_fonte)
        return ("Segoe UI", tamanho, peso)

    def _aplicar_estilos_ttk(self) -> None:
        """Atualiza estilos da Treeview e do Notebook conforme o tema e escala de fonte."""
        t = self.tema
        self.style.configure(
            "Treeview",
            background=t["bg_card"],
            foreground=t["fg_texto"],
            fieldbackground=t["bg_card"],
            rowheight=28 + (self.escala_fonte * 3),
            font=self._fonte(10),
        )
        self.style.configure(
            "Treeview.Heading",
            background=t["bg_header"],
            foreground=t["fg_header"],
            font=self._fonte(10, "bold"),
            padding=6,
        )
        self.style.map(
            "Treeview",
            background=[("selected", t["btn_primario_bg"])],
            foreground=[("selected", t["btn_primario_fg"])],
        )
        self.style.configure(
            "TNotebook",
            background=t["bg_principal"],
            borderwidth=0,
        )
        self.style.configure(
            "TNotebook.Tab",
            font=self._fonte(11, "bold"),
            padding=(16, 10),
            background=t["btn_secundario_bg"],
            foreground=t["btn_secundario_fg"],
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", t["btn_primario_bg"])],
            foreground=[("selected", t["btn_primario_fg"])],
        )

    # =========================================================================
    # Barra Superior de Identidade e Acessibilidade (ODS 8 / ODS 10 / ODS 3)
    # =========================================================================

    def _construir_barra_superior(self) -> None:
        if self.header_frame is not None:
            self.header_frame.destroy()

        t = self.tema
        self.header_frame = tk.Frame(self.root, bg=t["bg_header"], padx=16, pady=10)
        self.header_frame.pack(fill="x", side="top")

        bloco_esq = tk.Frame(self.header_frame, bg=t["bg_header"])
        bloco_esq.pack(side="left")

        lbl_brand = tk.Label(
            bloco_esq,
            text="👓 ÓTICA JURADO — Sistema de Gestão de Clientes e Receitas",
            font=self._fonte(14, "bold"),
            bg=t["bg_header"],
            fg=t["fg_header"],
        )
        lbl_brand.pack(anchor="w")

        usuario_txt = (
            f"Operador(a): {self.auth.usuario_atual['nome_exibicao']}"
            if self.auth.esta_autenticado()
            else "Acesso Restrito — Autenticação Obrigatória (RNF01)"
        )
        lbl_sub = tk.Label(
            bloco_esq,
            text=usuario_txt,
            font=self._fonte(9),
            bg=t["bg_header"],
            fg=t["fg_header"],
        )
        lbl_sub.pack(anchor="w")

        # Controles de Acessibilidade à direita
        bloco_dir = tk.Frame(self.header_frame, bg=t["bg_header"])
        bloco_dir.pack(side="right")

        texto_contraste = (
            "☀ Desativar Alto Contraste"
            if self.alto_contraste
            else "◐ Ativar Modo Alto Contraste (Acessibilidade)"
        )
        btn_contraste = tk.Button(
            bloco_dir,
            text=texto_contraste,
            font=self._fonte(9, "bold"),
            bg=t["btn_contraste_bg"],
            fg=t["btn_contraste_fg"],
            padx=10,
            pady=6,
            cursor="hand2",
            command=self.alternar_alto_contraste,
        )
        btn_contraste.pack(side="left", padx=4)

        btn_fonte_mais = tk.Button(
            bloco_dir,
            text="A+",
            font=self._fonte(9, "bold"),
            bg=t["btn_secundario_bg"],
            fg=t["btn_secundario_fg"],
            padx=8,
            pady=6,
            cursor="hand2",
            command=lambda: self.ajustar_fonte(1),
        )
        btn_fonte_mais.pack(side="left", padx=2)

        btn_fonte_menos = tk.Button(
            bloco_dir,
            text="A-",
            font=self._fonte(9, "bold"),
            bg=t["btn_secundario_bg"],
            fg=t["btn_secundario_fg"],
            padx=8,
            pady=6,
            cursor="hand2",
            command=lambda: self.ajustar_fonte(-1),
        )
        btn_fonte_menos.pack(side="left", padx=2)

        if self.auth.esta_autenticado():
            btn_sair = tk.Button(
                bloco_dir,
                text="Sair (Logout)",
                font=self._fonte(9, "bold"),
                bg=t["btn_alerta_bg"],
                fg=t["btn_alerta_fg"],
                padx=10,
                pady=6,
                cursor="hand2",
                command=self._realizar_logout,
            )
            btn_sair.pack(side="left", padx=(8, 0))

    def alternar_alto_contraste(self) -> None:
        """Alterna o Modo de Alto Contraste em toda a aplicação (ODS 10 e ODS 3)."""
        self.alto_contraste = not self.alto_contraste
        self.tema = self.TEMA_ALTO_CONTRASTE if self.alto_contraste else self.TEMA_PADRAO
        self._reconstruir_interface_atual()
        estado = "ATIVADO (Fundo Escuro / Letras Amarelas e Brancas)" if self.alto_contraste else "DESATIVADO (Padrão)"
        self.status_var.set(f"✔ Acessibilidade (ODS 10): Modo de Alto Contraste {estado}")

    def ajustar_fonte(self, delta: int) -> None:
        """Aumenta ou diminui dinamicamente o tamanho da fonte para acessibilidade visual."""
        novo = max(-1, min(3, self.escala_fonte + delta))
        if novo != self.escala_fonte:
            self.escala_fonte = novo
            self._reconstruir_interface_atual()
            self.status_var.set(f"✔ Acessibilidade: Escala de fonte ajustada ({self.escala_fonte:+d})")

    def _reconstruir_interface_atual(self) -> None:
        """Reaplica cores e fontes na tela ativa sem perder a sessão."""
        self.root.config(bg=self.tema["bg_principal"])
        if self.status_bar is not None:
            self.status_bar.config(
                bg="#1f1f1f" if self.alto_contraste else "#e9ecef",
                fg="#ffff00" if self.alto_contraste else "#212529",
                font=self._fonte(9, "bold"),
            )
        self._aplicar_estilos_ttk()
        self._construir_barra_superior()
        if self.auth.esta_autenticado():
            self.mostrar_painel_principal()
        else:
            self.mostrar_tela_login()

    def _limpar_body(self) -> None:
        if self.body_frame is not None:
            for widget in self.body_frame.winfo_children():
                widget.destroy()
            self.body_frame.config(bg=self.tema["bg_principal"])

    # =========================================================================
    # TELA 1: Menu Inicial e Autenticação Segura (RNF01)
    # =========================================================================

    def mostrar_tela_login(self) -> None:
        """Renderiza a Tela 1 do Protótipo: Autenticação Segura (RNF01)."""
        self._limpar_body()
        t = self.tema

        card = tk.Frame(
            self.body_frame,
            bg=t["bg_card"],
            padx=36,
            pady=32,
            highlightbackground=t["borda_foco"],
            highlightthickness=2,
        )
        card.place(relx=0.5, rely=0.48, anchor="center", width=460)

        lbl_titulo = tk.Label(
            card,
            text="Tela 1: Acesso ao Sistema",
            font=self._fonte(16, "bold"),
            bg=t["bg_card"],
            fg=t["fg_titulo"],
        )
        lbl_titulo.pack(pady=(0, 6))

        lbl_desc = tk.Label(
            card,
            text="Entre com suas credenciais para acessar o cadastro\nde clientes e o histórico de receitas da Ótica Jurado.",
            font=self._fonte(10),
            bg=t["bg_card"],
            fg=t["fg_subtexto"],
            justify="center",
        )
        lbl_desc.pack(pady=(0, 20))

        # Campo Usuário
        lbl_user = tk.Label(
            card,
            text="Nome de Usuário (Login) *:",
            font=self._fonte(10, "bold"),
            bg=t["bg_card"],
            fg=t["fg_texto"],
        )
        lbl_user.pack(anchor="w")

        self.entry_login_user = tk.Entry(
            card,
            font=self._fonte(11),
            bg=t["bg_input"],
            fg=t["fg_input"],
            insertbackground=t["fg_input"],
            highlightbackground=t["borda_foco"],
            highlightcolor=t["borda_foco"],
            highlightthickness=2,
        )
        self.entry_login_user.pack(fill="x", pady=(4, 14), ipady=6)
        self.entry_login_user.insert(0, "gerente")

        # Campo Senha
        lbl_pass = tk.Label(
            card,
            text="Senha de Acesso *:",
            font=self._fonte(10, "bold"),
            bg=t["bg_card"],
            fg=t["fg_texto"],
        )
        lbl_pass.pack(anchor="w")

        self.entry_login_pass = tk.Entry(
            card,
            font=self._fonte(11),
            show="•",
            bg=t["bg_input"],
            fg=t["fg_input"],
            insertbackground=t["fg_input"],
            highlightbackground=t["borda_foco"],
            highlightcolor=t["borda_foco"],
            highlightthickness=2,
        )
        self.entry_login_pass.pack(fill="x", pady=(4, 18), ipady=6)
        self.entry_login_pass.insert(0, "123456")

        # Botão de Acesso com altura >= 44px (Requisito de Acessibilidade)
        btn_entrar = tk.Button(
            card,
            text="🔐 Entrar no Sistema (Acessar)",
            font=self._fonte(11, "bold"),
            bg=t["btn_primario_bg"],
            fg=t["btn_primario_fg"],
            pady=10,
            cursor="hand2",
            command=self._processar_login,
        )
        btn_entrar.pack(fill="x", pady=(4, 12))

        lbl_dica = tk.Label(
            card,
            text="Credenciais de demonstração: Usuário: gerente | Senha: 123456\nSegurança RNF01: Senhas protegidas por hash criptográfico salgado.",
            font=self._fonte(8),
            bg=t["bg_card"],
            fg=t["fg_subtexto"],
            justify="center",
        )
        lbl_dica.pack(pady=(6, 0))

        self.entry_login_user.focus_set()
        self.entry_login_user.bind("<Return>", lambda _: self._processar_login())
        self.entry_login_pass.bind("<Return>", lambda _: self._processar_login())

    def _processar_login(self) -> None:
        username = self.entry_login_user.get()
        senha = self.entry_login_pass.get()
        try:
            usuario = self.auth.autenticar(username, senha)
            self.status_var.set(
                f"✔ Autenticação realizada com sucesso! Bem-vinda, {usuario['nome_exibicao']} (RNF01)."
            )
            self._construir_barra_superior()
            self.mostrar_painel_principal()
        except ValueError as err:
            messagebox.showerror("Falha de Autenticação (RNF01)", f"✖ {err}")

    def _realizar_logout(self) -> None:
        self.auth.encerrar_sessao()
        self._construir_barra_superior()
        self.mostrar_tela_login()
        self.status_var.set("✔ Sessão encerrada com segurança.")

    # =========================================================================
    # PAINEL PRINCIPAL: Abas para Tela 3 (Consulta) e Tela 2 (Cadastro)
    # =========================================================================

    def mostrar_painel_principal(self) -> None:
        """Exibe o painel principal com as Abas de Consulta (Tela 3) e Cadastro (Tela 2)."""
        self._limpar_body()
        t = self.tema

        self.notebook = ttk.Notebook(self.body_frame)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=10)

        self.aba_consulta = tk.Frame(self.notebook, bg=t["bg_principal"], padx=14, pady=12)
        self.aba_cadastro = tk.Frame(self.notebook, bg=t["bg_principal"], padx=14, pady=12)

        self.notebook.add(
            self.aba_consulta,
            text=" 🔍 Tela 3: Consulta de Clientes, CPF e Histórico de Receitas (RF03) ",
        )
        self.notebook.add(
            self.aba_cadastro,
            text=" ➕ Tela 2: Cadastro de Cliente e Nova Receita / Venda (RF01 / RF02) ",
        )

        self._construir_aba_consulta()
        self._construir_aba_cadastro()

    # =========================================================================
    # TELA 3: Consulta Rápida por Nome / CPF e Histórico (RF03 e RNF03)
    # =========================================================================

    def _construir_aba_consulta(self) -> None:
        t = self.tema

        # Barra de Pesquisa
        card_busca = tk.Frame(
            self.aba_consulta,
            bg=t["bg_card"],
            padx=16,
            pady=12,
            highlightbackground=t["borda_foco"],
            highlightthickness=1,
        )
        card_busca.pack(fill="x", pady=(0, 10))

        lbl_instrucao = tk.Label(
            card_busca,
            text="Digite o Nome, CPF do Cliente ou Tipo de Lente para buscar:",
            font=self._fonte(10, "bold"),
            bg=t["bg_card"],
            fg=t["fg_texto"],
        )
        lbl_instrucao.pack(side="left", padx=(0, 10))

        self.entry_busca = tk.Entry(
            card_busca,
            font=self._fonte(11),
            width=34,
            bg=t["bg_input"],
            fg=t["fg_input"],
            insertbackground=t["fg_input"],
            highlightbackground=t["borda_foco"],
            highlightcolor=t["borda_foco"],
            highlightthickness=2,
        )
        self.entry_busca.pack(side="left", padx=(0, 10), ipady=5)
        self.entry_busca.bind("<Return>", lambda _: self.atualizar_tabela_consulta())
        self.entry_busca.bind("<KeyRelease>", lambda _: self.atualizar_tabela_consulta())

        btn_pesquisar = tk.Button(
            card_busca,
            text="🔍 Pesquisar no Sistema",
            font=self._fonte(10, "bold"),
            bg=t["btn_primario_bg"],
            fg=t["btn_primario_fg"],
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.atualizar_tabela_consulta,
        )
        btn_pesquisar.pack(side="left", padx=(0, 8))

        btn_mostrar_todos = tk.Button(
            card_busca,
            text="Mostrar Todos",
            font=self._fonte(10),
            bg=t["btn_secundario_bg"],
            fg=t["btn_secundario_fg"],
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._limpar_filtro_busca,
        )
        btn_mostrar_todos.pack(side="left")

        self.lbl_metricas_busca = tk.Label(
            card_busca,
            text="",
            font=self._fonte(9, "bold"),
            bg=t["bg_card"],
            fg=t["status_ok"],
        )
        self.lbl_metricas_busca.pack(side="right")

        # Tabela Treeview
        frame_tabela = tk.Frame(self.aba_consulta, bg=t["bg_card"])
        frame_tabela.pack(fill="both", expand=True, pady=(0, 10))

        colunas = (
            "id_cliente",
            "nome",
            "cpf",
            "telefone",
            "data_receita",
            "grau_od",
            "grau_oe",
            "tipo_lente",
            "valor",
            "status",
        )
        self.tree = ttk.Treeview(
            frame_tabela,
            columns=colunas,
            show="headings",
            selectmode="browse",
        )

        definicoes_colunas = [
            ("id_cliente", "ID", 45, "center"),
            ("nome", "Nome do Cliente", 170, "w"),
            ("cpf", "CPF", 120, "center"),
            ("telefone", "Telefone", 115, "center"),
            ("data_receita", "Última Compra", 100, "center"),
            ("grau_od", "Grau OD (Esf/Cil)", 115, "center"),
            ("grau_oe", "Grau OE (Esf/Cil)", 115, "center"),
            ("tipo_lente", "Tipo de Lente", 185, "w"),
            ("valor", "Valor", 85, "e"),
            ("status", "Status do Pedido", 160, "center"),
        ]
        for col_id, titulo, largura, alinhamento in definicoes_colunas:
            self.tree.heading(col_id, text=titulo)
            self.tree.column(col_id, width=largura, anchor=alinhamento)

        scroll_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda _: self.abrir_janela_detalhes_selecionado())

        # Barra de Botões de Ação Inferior
        frame_acoes = tk.Frame(self.aba_consulta, bg=t["bg_principal"])
        frame_acoes.pack(fill="x")

        btn_detalhes = tk.Button(
            frame_acoes,
            text="📋 Abrir Ficha Completa e Histórico (Tela Secundária)",
            font=self._fonte(10, "bold"),
            bg=t["btn_primario_bg"],
            fg=t["btn_primario_fg"],
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.abrir_janela_detalhes_selecionado,
        )
        btn_detalhes.pack(side="left", padx=(0, 8))

        btn_ir_cadastro = tk.Button(
            frame_acoes,
            text="➕ Cadastrar Novo Cliente / Receita",
            font=self._fonte(10, "bold"),
            bg=t["btn_sucesso_bg"],
            fg=t["btn_sucesso_fg"],
            padx=14,
            pady=8,
            cursor="hand2",
            command=lambda: self.notebook.select(self.aba_cadastro),
        )
        btn_ir_cadastro.pack(side="left", padx=(0, 8))

        btn_exportar_csv = tk.Button(
            frame_acoes,
            text="📊 Exportar Relatório CSV (RF04)",
            font=self._fonte(10, "bold"),
            bg=t["btn_secundario_bg"],
            fg=t["btn_secundario_fg"],
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.acao_exportar_csv,
        )
        btn_exportar_csv.pack(side="left", padx=(0, 8))

        btn_excluir = tk.Button(
            frame_acoes,
            text="🗑️ Excluir Cliente",
            font=self._fonte(10, "bold"),
            bg=t["btn_alerta_bg"],
            fg=t["btn_alerta_fg"],
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.acao_excluir_cliente_selecionado,
        )
        btn_excluir.pack(side="right")

        self.atualizar_tabela_consulta()

    def _limpar_filtro_busca(self) -> None:
        self.entry_busca.delete(0, tk.END)
        self.atualizar_tabela_consulta()

    def atualizar_tabela_consulta(self) -> None:
        """Executa a busca parametrizada e popula a tabela medindo o tempo (RNF03)."""
        termo = self.entry_busca.get() if hasattr(self, "entry_busca") else ""
        registros, tempo_ms = self.service.buscar_historico_clientes(termo)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for reg in registros:
            grau_od = f"{reg.get('grau_esf_od') or '-'} ({reg.get('grau_cil_od') or '0.00'})"
            grau_oe = f"{reg.get('grau_esf_oe') or '-'} ({reg.get('grau_cil_oe') or '0.00'})"
            val_num = float(reg.get("valor_venda") or 0.0)
            valor_str = f"R$ {val_num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self.tree.insert(
                "",
                "end",
                values=(
                    reg["id_cliente"],
                    reg["nome"],
                    reg["cpf"],
                    reg["telefone"],
                    reg.get("data_receita") or "-",
                    grau_od,
                    grau_oe,
                    reg.get("tipo_lente") or "-",
                    valor_str,
                    reg.get("status_pedido") or "-",
                ),
            )

        if self.tree.get_children():
            primeiro = self.tree.get_children()[0]
            self.tree.selection_set(primeiro)

        self.lbl_metricas_busca.config(
            text=f"✔ {len(registros)} registo(s) em {tempo_ms:.1f} ms (Meta RNF03 < 2000 ms)"
        )

    def abrir_janela_detalhes_selecionado(self) -> None:
        """
        Abre a Janela Secundária dedicada com todo o histórico de compras,
        especificação de lente (ex: Crizal Acrílica) e botão de Orçamento/Impressão.
        """
        selecao = self.tree.selection()
        if not selecao:
            messagebox.showwarning(
                "Selecione um Cliente",
                "Por favor, selecione um cliente na tabela (ou pesquise pelo CPF/Nome) para abrir a ficha detalhada.",
            )
            return

        valores = self.tree.item(selecao[0], "values")
        id_cliente = int(valores[0])
        ficha = self.service.obter_ficha_completa_cliente(id_cliente)
        cli = ficha["cliente"]
        receitas = ficha["receitas"]

        t = self.tema
        janela = tk.Toplevel(self.root)
        janela.title(f"Histórico do Cliente e Lentes - {cli['nome']} (Ótica Jurado)")
        janela.geometry("650x520")
        janela.config(bg=t["bg_principal"])

        header = tk.Frame(janela, bg=t["bg_header"], padx=16, pady=12)
        header.pack(fill="x")

        lbl_h = tk.Label(
            header,
            text="Histórico de Compras e Receita Óptica",
            font=self._fonte(13, "bold"),
            bg=t["bg_header"],
            fg=t["fg_header"],
        )
        lbl_h.pack(anchor="w")

        card_info = tk.Frame(
            janela,
            bg=t["bg_card"],
            padx=18,
            pady=14,
            highlightbackground=t["borda_foco"],
            highlightthickness=1,
        )
        card_info.pack(fill="both", expand=True, padx=16, pady=12)

        txt_detalhes = tk.Text(
            card_info,
            font=("Consolas", max(10, 10 + self.escala_fonte)),
            bg=t["bg_card"],
            fg=t["fg_texto"],
            relief="flat",
            wrap="word",
        )
        txt_detalhes.pack(fill="both", expand=True)

        conteudo_orcamento = self.service.gerar_orcamento_txt(id_cliente)
        txt_detalhes.insert("1.0", conteudo_orcamento)
        txt_detalhes.config(state="disabled")

        rodape = tk.Frame(janela, bg=t["bg_principal"], padx=16, pady=8)
        rodape.pack(fill="x")

        def salvar_orcamento():
            caminho = filedialog.asksaveasfilename(
                parent=janela,
                title="Salvar Ficha / Orçamento do Cliente",
                defaultextension=".txt",
                initialfile=f"ficha_{cli['nome'].lower().replace(' ', '_')}.txt",
                filetypes=[("Arquivo de Texto", "*.txt"), ("Todos os arquivos", "*.*")],
            )
            if caminho:
                self.service.gerar_orcamento_txt(id_cliente, caminho)
                messagebox.showinfo(
                    "Ficha / Orçamento Salvo",
                    f"✔ Ficha e orçamento do cliente {cli['nome']} gerados com sucesso em:\n{caminho}",
                    parent=janela,
                )

        btn_imprimir = tk.Button(
            rodape,
            text="🖨️ Salvar / Imprimir Orçamento e Ficha (TXT)",
            font=self._fonte(10, "bold"),
            bg=t["btn_sucesso_bg"],
            fg=t["btn_sucesso_fg"],
            padx=14,
            pady=6,
            cursor="hand2",
            command=salvar_orcamento,
        )
        btn_imprimir.pack(side="left")

        btn_nova_receita_cli = tk.Button(
            rodape,
            text="➕ Adicionar Nova Compra para este Cliente",
            font=self._fonte(10, "bold"),
            bg=t["btn_primario_bg"],
            fg=t["btn_primario_fg"],
            padx=14,
            pady=6,
            cursor="hand2",
            command=lambda: [janela.destroy(), self._preencher_cliente_no_cadastro(cli)],
        )
        btn_nova_receita_cli.pack(side="left", padx=8)

        btn_fechar = tk.Button(
            rodape,
            text="Fechar",
            font=self._fonte(10, "bold"),
            bg=t["btn_secundario_bg"],
            fg=t["btn_secundario_fg"],
            padx=14,
            pady=6,
            cursor="hand2",
            command=janela.destroy,
        )
        btn_fechar.pack(side="right")

    def _preencher_cliente_no_cadastro(self, cli: Dict[str, Any]) -> None:
        """Preenche os dados do cliente na Aba 2 para lançar uma nova receita rapidamente."""
        self.notebook.select(self.aba_cadastro)
        self._limpar_formulario_cadastro()
        self.campos_cad["nome"].insert(0, cli.get("nome", ""))
        self.campos_cad["cpf"].insert(0, cli.get("cpf", ""))
        self.campos_cad["telefone"].insert(0, cli.get("telefone", ""))
        self.campos_cad["data_nascimento"].insert(0, cli.get("data_nascimento", ""))
        self.campos_cad["endereco"].insert(0, cli.get("endereco", ""))
        self.campos_cad["grau_esf_od"].focus_set()

    def acao_exportar_csv(self) -> None:
        """Exporta os dados para CSV (RF04)."""
        caminho = filedialog.asksaveasfilename(
            title="Exportar Relatório de Clientes e Receitas (CSV)",
            defaultextension=".csv",
            initialfile=f"relatorio_otica_jurado_{datetime.now().strftime('%Y%m%d')}.csv",
            filetypes=[("Planilha CSV", "*.csv")],
        )
        if caminho:
            termo = self.entry_busca.get()
            arq = self.service.exportar_relatorio_csv(caminho, termo)
            self.status_var.set(f"✔ Relatório CSV exportado com sucesso: {arq}")
            messagebox.showinfo(
                "Exportação Concluída (RF04)",
                f"✔ Relatório exportado com sucesso para:\n{arq}",
            )

    def acao_excluir_cliente_selecionado(self) -> None:
        selecao = self.tree.selection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione um registro na tabela para excluir.")
            return
        valores = self.tree.item(selecao[0], "values")
        id_cliente = int(valores[0])
        nome = valores[1]
        if messagebox.askyesno(
            "Confirmar Exclusão",
            f"Deseja realmente excluir o cadastro e o histórico de '{nome}'?",
        ):
            self.service.db.excluir_cliente(id_cliente)
            self.atualizar_tabela_consulta()
            self.status_var.set(f"✔ Cliente '{nome}' removido com sucesso.")

    # =========================================================================
    # TELA 2: Cadastro de Clientes, Receitas e Vendas (RF01, RF02, RNF02)
    # =========================================================================

    def _construir_aba_cadastro(self) -> None:
        t = self.tema
        self.campos_cad: Dict[str, Any] = {}

        card_form = tk.Frame(
            self.aba_cadastro,
            bg=t["bg_card"],
            padx=22,
            pady=16,
            highlightbackground=t["borda_foco"],
            highlightthickness=1,
        )
        card_form.pack(fill="both", expand=True)

        # Cabeçalho do Formulário
        lbl_t2 = tk.Label(
            card_form,
            text="Tela 2: Cadastro de Cliente e Receita Oftalmológica (RF01 e RF02)",
            font=self._fonte(13, "bold"),
            bg=t["bg_card"],
            fg=t["fg_titulo"],
        )
        lbl_t2.pack(anchor="w", pady=(0, 12))

        grid_frame = tk.Frame(card_form, bg=t["bg_card"])
        grid_frame.pack(fill="x")
        for col in range(4):
            grid_frame.columnconfigure(col, weight=1, pad=8)

        def criar_campo(parent, row: int, col: int, chave: str, rotulo: str, valor_inicial: str = "", colspan: int = 1):
            frame_c = tk.Frame(parent, bg=t["bg_card"])
            frame_c.grid(row=row, column=col, columnspan=colspan, sticky="ew", padx=6, pady=5)
            lbl = tk.Label(
                frame_c,
                text=rotulo,
                font=self._fonte(9, "bold"),
                bg=t["bg_card"],
                fg=t["fg_texto"],
            )
            lbl.pack(anchor="w")
            ent = tk.Entry(
                frame_c,
                font=self._fonte(10),
                bg=t["bg_input"],
                fg=t["fg_input"],
                insertbackground=t["fg_input"],
                highlightbackground=t["borda_foco"],
                highlightcolor=t["borda_foco"],
                highlightthickness=1,
            )
            ent.pack(fill="x", ipady=4, pady=(2, 0))
            if valor_inicial:
                ent.insert(0, valor_inicial)
            self.campos_cad[chave] = ent
            return ent

        # Linha 0 e 1: Dados Pessoais do Cliente (RF01)
        criar_campo(grid_frame, 0, 0, "nome", "Nome Completo do Cliente *:", colspan=2)
        criar_campo(grid_frame, 0, 2, "cpf", "CPF (11 dígitos) *:")
        criar_campo(grid_frame, 0, 3, "telefone", "Telefone / WhatsApp *:")

        criar_campo(grid_frame, 1, 0, "data_nascimento", "Data de Nascimento (DD/MM/AAAA):")
        criar_campo(grid_frame, 1, 1, "endereco", "Endereço Completo:", colspan=3)

        # Separador Visual
        sep = tk.Frame(card_form, height=2, bg=t["borda_foco"])
        sep.pack(fill="x", pady=12)

        lbl_rec = tk.Label(
            card_form,
            text="Parâmetros da Receita Óptica (Dioptrias OD / OE) e Dados da Venda (RF02)",
            font=self._fonte(11, "bold"),
            bg=t["bg_card"],
            fg=t["fg_titulo"],
        )
        lbl_rec.pack(anchor="w", pady=(0, 8))

        grid_rec = tk.Frame(card_form, bg=t["bg_card"])
        grid_rec.pack(fill="x")
        for col in range(4):
            grid_rec.columnconfigure(col, weight=1, pad=8)

        # Linha 0 da Receita: Olho Direito (OD) + Adição
        criar_campo(grid_rec, 0, 0, "grau_esf_od", "Grau Esférico OD * (ex: -2.25):", "-2.00")
        criar_campo(grid_rec, 0, 1, "grau_cil_od", "Grau Cilíndrico OD (ex: -0.50):", "0.00")
        criar_campo(grid_rec, 0, 2, "eixo_od", "Eixo OD (ex: 180°):", "0°")
        criar_campo(grid_rec, 0, 3, "adicao", "Adição Perto (ex: +2.00):", "0.00")

        # Linha 1 da Receita: Olho Esquerdo (OE) + DNP
        criar_campo(grid_rec, 1, 0, "grau_esf_oe", "Grau Esférico OE * (ex: -1.75):", "-1.75")
        criar_campo(grid_rec, 1, 1, "grau_cil_oe", "Grau Cilíndrico OE (ex: -0.25):", "0.00")
        criar_campo(grid_rec, 1, 2, "eixo_oe", "Eixo OE (ex: 175°):", "0°")
        criar_campo(grid_rec, 1, 3, "dnp", "DNP (ex: 31/31 mm):", "31/31 mm")

        # Linha 2 da Receita: Tipo de Lente, Armação, Valor, Data
        frame_lente = tk.Frame(grid_rec, bg=t["bg_card"])
        frame_lente.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=5)
        tk.Label(
            frame_lente,
            text="Tipo de Lente Escolhida *:",
            font=self._fonte(9, "bold"),
            bg=t["bg_card"],
            fg=t["fg_texto"],
        ).pack(anchor="w")
        combo_lente = ttk.Combobox(
            frame_lente,
            font=self._fonte(10),
            values=[
                "Crizal Acrílica",
                "Policarbonato Blue Control (Filtro Luz Azul)",
                "Multifocal Varilux Comfort Crizal",
                "Multifocal Digital Crizal Easy Pro",
                "Resina Antirreflexo Simples",
                "Lente Alto Índice 1.67 Antirreflexo",
            ],
        )
        combo_lente.pack(fill="x", ipady=3, pady=(2, 0))
        combo_lente.set("Crizal Acrílica")
        self.campos_cad["tipo_lente"] = combo_lente

        criar_campo(grid_rec, 2, 2, "armacao", "Armação:", "Acetato Preto Classic")
        criar_campo(grid_rec, 2, 3, "valor_venda", "Valor da Venda (R$):", "680,00")

        # Linha 3: Data da Compra, Status e Observações
        criar_campo(
            grid_rec,
            3,
            0,
            "data_receita",
            "Data da Compra / Receita *:",
            datetime.now().strftime("%d/%m/%Y"),
        )

        frame_status = tk.Frame(grid_rec, bg=t["bg_card"])
        frame_status.grid(row=3, column=1, sticky="ew", padx=6, pady=5)
        tk.Label(
            frame_status,
            text="Status do Pedido:",
            font=self._fonte(9, "bold"),
            bg=t["bg_card"],
            fg=t["fg_texto"],
        ).pack(anchor="w")
        combo_status = ttk.Combobox(
            frame_status,
            font=self._fonte(10),
            values=[
                "Pedido Entregue / Concluído",
                "Pronto para Montagem",
                "No Laboratório",
                "Aguardando Lentes",
            ],
        )
        combo_status.pack(fill="x", ipady=3, pady=(2, 0))
        combo_status.set("Pedido Entregue / Concluído")
        self.campos_cad["status_pedido"] = combo_status

        criar_campo(grid_rec, 3, 2, "observacoes", "Observações Clínicas / Montagem:", colspan=2)

        # Botões de Ação do Cadastro (altura >= 44px)
        frame_botoes_cad = tk.Frame(card_form, bg=t["bg_card"])
        frame_botoes_cad.pack(fill="x", pady=(18, 0))

        btn_salvar = tk.Button(
            frame_botoes_cad,
            text="💾 Salvar Cliente e Receita no Sistema (RF01 / RF02)",
            font=self._fonte(11, "bold"),
            bg=t["btn_sucesso_bg"],
            fg=t["btn_sucesso_fg"],
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.acao_salvar_cadastro,
        )
        btn_salvar.pack(side="left", padx=(0, 12))

        btn_limpar = tk.Button(
            frame_botoes_cad,
            text="🧹 Limpar Formulário",
            font=self._fonte(10, "bold"),
            bg=t["btn_secundario_bg"],
            fg=t["btn_secundario_fg"],
            padx=14,
            pady=10,
            cursor="hand2",
            command=self._limpar_formulario_cadastro,
        )
        btn_limpar.pack(side="left")

    def _limpar_formulario_cadastro(self) -> None:
        for chave, widget in self.campos_cad.items():
            if isinstance(widget, ttk.Combobox):
                if chave == "tipo_lente":
                    widget.set("Crizal Acrílica")
                elif chave == "status_pedido":
                    widget.set("Pedido Entregue / Concluído")
            else:
                widget.delete(0, tk.END)
                if chave in ("grau_cil_od", "grau_cil_oe", "adicao"):
                    widget.insert(0, "0.00")
                elif chave in ("eixo_od", "eixo_oe"):
                    widget.insert(0, "0°")
                elif chave == "data_receita":
                    widget.insert(0, datetime.now().strftime("%d/%m/%Y"))

    def acao_salvar_cadastro(self) -> None:
        """Valida e grava os dados do formulário no banco de dados (RF01, RF02 e RNF02)."""
        dados = {k: w.get() for k, w in self.campos_cad.items()}
        try:
            id_cliente, id_receita = self.service.cadastrar_cliente_com_receita(**dados)
            self.atualizar_tabela_consulta()
            self.status_var.set(
                f"✔ Registro salvo com sucesso! Cliente ID #{id_cliente} | Receita ID #{id_receita}"
            )
            messagebox.showinfo(
                "Cadastro Concluído com Sucesso",
                f"✔ Cliente '{dados['nome']}' e receita óptica ({dados['tipo_lente']}) "
                "foram gravados com segurança no banco de dados!",
            )
            self._limpar_formulario_cadastro()
            self.notebook.select(self.aba_consulta)
        except (ValueError, PermissionError, RuntimeError) as err:
            messagebox.showwarning("Validação de Dados (RNF02)", f"⚠ {err}")
