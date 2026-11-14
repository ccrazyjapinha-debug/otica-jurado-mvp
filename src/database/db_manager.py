"""
Camada de Persistência e Acesso a Dados (DAO) - Ótica Jurado.

Implementa:
- Arquitetura em Camadas: Isolamento total do SQL em relação à interface Tkinter.
- RNF02 (OWASP A03:2021 - Injection): Uso estrito de Consultas Parametrizadas
  (Prepared Statements) em todas as operações de leitura e escrita.
- RNF03 (Desempenho < 2s): Criação de índices nas colunas de busca (nome e CPF).
- Portabilidade: Suporte a MySQL (via PyMySQL) e banco relacional local embarcado
  (SQLite3) para funcionamento imediato offline no computador da ótica.
"""

import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.auth_service import AuthService

try:
    import pymysql  # type: ignore
    import pymysql.cursors  # type: ignore
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False


class DatabaseManager:
    """Gerenciador de banco de dados relacional com consultas parametrizadas."""

    def __init__(self, db_path: Optional[str] = None, use_mysql: bool = False) -> None:
        self.use_mysql = use_mysql and HAS_PYMYSQL
        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            data_dir = base_dir / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "otica_jurado.db")
        else:
            self.db_path = db_path

        self._memory_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:" and not self.use_mysql:
            self._memory_conn = sqlite3.connect(":memory:")
            self._memory_conn.row_factory = sqlite3.Row
            self._memory_conn.execute("PRAGMA foreign_keys = ON;")

        self.inicializar_banco()

    def _get_connection(self):
        """Retorna uma conexão ativa com o banco de dados configurado."""
        if self.use_mysql:
            return pymysql.connect(
                host=os.getenv("MYSQL_HOST", "localhost"),
                user=os.getenv("MYSQL_USER", "root"),
                password=os.getenv("MYSQL_PASSWORD", ""),
                database=os.getenv("MYSQL_DB", "otica_jurado"),
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
            )

        if self._memory_conn is not None:
            return self._memory_conn

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _close_if_needed(self, conn) -> None:
        """Fecha a conexão se não for um banco em memória persistente para testes."""
        if conn is not self._memory_conn:
            conn.close()

    def close(self) -> None:
        """Fecha explicitamente a conexão em memória (usada em testes automatizados)."""
        if self._memory_conn is not None:
            self._memory_conn.close()
            self._memory_conn = None

    def inicializar_banco(self) -> None:
        """Cria tabelas, índices de desempenho (RNF03) e dados iniciais de demonstração."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    nome_exibicao TEXT NOT NULL,
                    senha_hash TEXT NOT NULL,
                    papel TEXT DEFAULT 'Gestora',
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS clientes (
                    id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    cpf TEXT NOT NULL UNIQUE,
                    telefone TEXT NOT NULL,
                    data_nascimento TEXT DEFAULT '',
                    endereco TEXT DEFAULT '',
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS receitas (
                    id_receita INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_cliente INTEGER NOT NULL,
                    grau_esf_od TEXT NOT NULL,
                    grau_cil_od TEXT DEFAULT '0.00',
                    eixo_od TEXT DEFAULT '0°',
                    grau_esf_oe TEXT NOT NULL,
                    grau_cil_oe TEXT DEFAULT '0.00',
                    eixo_oe TEXT DEFAULT '0°',
                    adicao TEXT DEFAULT '0.00',
                    dnp TEXT DEFAULT '',
                    tipo_lente TEXT NOT NULL,
                    armacao TEXT DEFAULT '',
                    valor_venda REAL DEFAULT 0.0,
                    data_receita TEXT NOT NULL,
                    status_pedido TEXT DEFAULT 'Pedido Entregue / Concluído',
                    observacoes TEXT DEFAULT '',
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE CASCADE
                )
                """
            )
            # Índices para garantir RNF03 (< 2 segundos)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_clientes_nome ON clientes(nome)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_clientes_cpf ON clientes(cpf)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_receitas_cliente ON receitas(id_cliente)")
            conn.commit()
        finally:
            self._close_if_needed(conn)

        self._popular_dados_iniciais()

    def _popular_dados_iniciais(self) -> None:
        """Popula usuários padrão e fichas iniciais caso o banco esteja vazio."""
        if not self.buscar_usuario_por_username("gerente"):
            hash_padrao = AuthService.gerar_hash_senha("123456")
            self.criar_usuario("gerente", "Marcia Jurado (Gestora)", hash_padrao, "Gestora")
            self.criar_usuario("marcia", "Marcia Jurado", hash_padrao, "Proprietária")

        if self.contar_clientes() == 0:
            # 1. João da Silva (exemplo clássico da Atividade 3 com Crizal Acrílica)
            id_joao = self.inserir_cliente(
                nome="João da Silva",
                cpf="479.290.358-08",
                telefone="(11) 99123-4567",
                data_nascimento="14/03/1978",
                endereco="Rua das Flores, 120 - Centro",
            )
            self.inserir_receita(
                id_cliente=id_joao,
                grau_esf_od="-2.00",
                grau_cil_od="-0.25",
                eixo_od="180°",
                grau_esf_oe="-1.50",
                grau_cil_oe="-0.25",
                eixo_oe="175°",
                adicao="+1.75",
                dnp="31/31 mm",
                tipo_lente="Resina Antirreflexo Simples",
                armacao="Metal Prata Retangular",
                valor_venda=420.00,
                data_receita="12/08/2024",
                status_pedido="Pedido Entregue / Concluído",
                observacoes="Primeira ficha migrada do fichário físico.",
            )
            self.inserir_receita(
                id_cliente=id_joao,
                grau_esf_od="-2.25",
                grau_cil_od="-0.50",
                eixo_od="180°",
                grau_esf_oe="-1.75",
                grau_cil_oe="-0.25",
                eixo_oe="175°",
                adicao="+2.00",
                dnp="31/31 mm",
                tipo_lente="Crizal Acrílica",
                armacao="Acetato Preto Classic",
                valor_venda=680.00,
                data_receita="10/10/2026",
                status_pedido="Pedido Entregue / Concluído",
                observacoes="Cliente elogiou o conforto visual da lente Crizal Acrílica.",
            )

            # 2. Maria da Silva (exemplo do Protótipo e Validação da Atividade 2)
            id_maria = self.inserir_cliente(
                nome="Maria da Silva",
                cpf="321.654.987-01",
                telefone="(11) 98765-4321",
                data_nascimento="22/07/1985",
                endereco="Av. Brasil, 450 - Bairro Jardim",
            )
            self.inserir_receita(
                id_cliente=id_maria,
                grau_esf_od="-2.00",
                grau_cil_od="-0.75",
                eixo_od="90°",
                grau_esf_oe="-1.75",
                grau_cil_oe="-0.50",
                eixo_oe="85°",
                adicao="0.00",
                dnp="30/30 mm",
                tipo_lente="Policarbonato Blue Control (Filtro Luz Azul)",
                armacao="Metal Dourado Redondo",
                valor_venda=540.00,
                data_receita="12/05/2026",
                status_pedido="Pedido Entregue / Concluído",
                observacoes="Uso diário no computador.",
            )

            # 3. João Pereira (exemplo do Protótipo da Tela 3)
            id_pereira = self.inserir_cliente(
                nome="João Pereira",
                cpf="123.456.789-10",
                telefone="(11) 91234-5678",
                data_nascimento="09/11/1969",
                endereco="Rua São José, 88 - Vila Nova",
            )
            self.inserir_receita(
                id_cliente=id_pereira,
                grau_esf_od="-1.00",
                grau_cil_od="0.00",
                eixo_od="0°",
                grau_esf_oe="-1.25",
                grau_cil_oe="-0.25",
                eixo_oe="180°",
                adicao="+1.50",
                dnp="32/31.5 mm",
                tipo_lente="Multifocal Varilux Comfort Crizal",
                armacao="Titânio Cinza Leve",
                valor_venda=1290.00,
                data_receita="15/09/2026",
                status_pedido="Pronto para Montagem",
                observacoes="Avisar cliente no WhatsApp assim que finalizar montagem.",
            )

            # 4. Ana Paula Oliveira
            id_ana = self.inserir_cliente(
                nome="Ana Paula Oliveira",
                cpf="852.741.963-44",
                telefone="(11) 97654-3210",
                data_nascimento="03/02/1974",
                endereco="Rua Tiradentes, 310 - Centro",
            )
            self.inserir_receita(
                id_cliente=id_ana,
                grau_esf_od="+1.50",
                grau_cil_od="-0.50",
                eixo_od="100°",
                grau_esf_oe="+1.75",
                grau_cil_oe="-0.50",
                eixo_oe="80°",
                adicao="+2.25",
                dnp="29.5/30 mm",
                tipo_lente="Multifocal Digital Crizal Easy Pro",
                armacao="Acetato Tartaruga Feminino",
                valor_venda=980.00,
                data_receita="05/11/2026",
                status_pedido="No Laboratório",
                observacoes="Previsão de retorno do laboratório em 3 dias úteis.",
            )

    # =========================================================================
    # Operações de Usuários (RNF01)
    # =========================================================================

    def criar_usuario(
        self, username: str, nome_exibicao: str, senha_hash: str, papel: str = "Gestora"
    ) -> int:
        """Insere um novo usuário com senha criptografada via Prepared Statement."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO usuarios (username, nome_exibicao, senha_hash, papel)
                VALUES (?, ?, ?, ?)
                """,
                (username.strip().lower(), nome_exibicao.strip(), senha_hash, papel),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            self._close_if_needed(conn)

    def buscar_usuario_por_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Busca usuário pelo login usando consulta parametrizada."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM usuarios WHERE username = ?",
                (username.strip().lower(),),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            self._close_if_needed(conn)

    # =========================================================================
    # Operações de Clientes (RF01)
    # =========================================================================

    def inserir_cliente(
        self,
        nome: str,
        cpf: str,
        telefone: str,
        data_nascimento: str = "",
        endereco: str = "",
    ) -> int:
        """Insere um novo cliente no banco de dados (RF01 e RNF02)."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO clientes (nome, cpf, telefone, data_nascimento, endereco)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    nome.strip(),
                    cpf.strip(),
                    telefone.strip(),
                    data_nascimento.strip(),
                    endereco.strip(),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            self._close_if_needed(conn)

    def atualizar_cliente(
        self,
        id_cliente: int,
        nome: str,
        cpf: str,
        telefone: str,
        data_nascimento: str = "",
        endereco: str = "",
    ) -> bool:
        """Atualiza os dados cadastrais de um cliente existente."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE clientes
                SET nome = ?, cpf = ?, telefone = ?, data_nascimento = ?, endereco = ?
                WHERE id_cliente = ?
                """,
                (
                    nome.strip(),
                    cpf.strip(),
                    telefone.strip(),
                    data_nascimento.strip(),
                    endereco.strip(),
                    int(id_cliente),
                ),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            self._close_if_needed(conn)

    def excluir_cliente(self, id_cliente: int) -> bool:
        """Remove um cliente e suas receitas associadas."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM clientes WHERE id_cliente = ?", (int(id_cliente),))
            conn.commit()
            return cur.rowcount > 0
        finally:
            self._close_if_needed(conn)

    def buscar_cliente_por_id(self, id_cliente: int) -> Optional[Dict[str, Any]]:
        """Retorna um cliente pelo seu ID único."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM clientes WHERE id_cliente = ?", (int(id_cliente),))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            self._close_if_needed(conn)

    def buscar_cliente_por_cpf(self, cpf: str) -> Optional[Dict[str, Any]]:
        """Busca um cliente pelo CPF (formatado ou apenas dígitos) usando Prepared Statement."""
        apenas_digitos = re.sub(r"\D", "", cpf or "")
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM clientes
                WHERE cpf = ?
                   OR REPLACE(REPLACE(cpf, '.', ''), '-', '') = ?
                """,
                (cpf.strip(), apenas_digitos),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            self._close_if_needed(conn)

    def listar_clientes(self, termo_busca: str = "") -> List[Dict[str, Any]]:
        """Lista clientes filtrando por nome ou CPF via consulta parametrizada (RF03)."""
        termo = (termo_busca or "").strip()
        apenas_digitos = re.sub(r"\D", "", termo)
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if not termo:
                cur.execute("SELECT * FROM clientes ORDER BY nome ASC")
            else:
                like_term = f"%{termo}%"
                like_digits = f"%{apenas_digitos}%" if apenas_digitos else like_term
                cur.execute(
                    """
                    SELECT * FROM clientes
                    WHERE nome LIKE ?
                       OR cpf LIKE ?
                       OR REPLACE(REPLACE(cpf, '.', ''), '-', '') LIKE ?
                       OR telefone LIKE ?
                    ORDER BY nome ASC
                    """,
                    (like_term, like_term, like_digits, like_term),
                )
            return [dict(r) for r in cur.fetchall()]
        finally:
            self._close_if_needed(conn)

    def contar_clientes(self) -> int:
        """Retorna o total de clientes cadastrados."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS total FROM clientes")
            row = cur.fetchone()
            return int(row["total"]) if row else 0
        finally:
            self._close_if_needed(conn)

    # =========================================================================
    # Operações de Receitas e Vendas Ópticas (RF02 e RF03)
    # =========================================================================

    def inserir_receita(
        self,
        id_cliente: int,
        grau_esf_od: str,
        grau_esf_oe: str,
        tipo_lente: str,
        data_receita: str,
        grau_cil_od: str = "0.00",
        eixo_od: str = "0°",
        grau_cil_oe: str = "0.00",
        eixo_oe: str = "0°",
        adicao: str = "0.00",
        dnp: str = "",
        armacao: str = "",
        valor_venda: float = 0.0,
        status_pedido: str = "Pedido Entregue / Concluído",
        observacoes: str = "",
    ) -> int:
        """Registra uma nova receita/venda vinculada a um cliente válido (RF02)."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO receitas (
                    id_cliente, grau_esf_od, grau_cil_od, eixo_od,
                    grau_esf_oe, grau_cil_oe, eixo_oe, adicao, dnp,
                    tipo_lente, armacao, valor_venda, data_receita,
                    status_pedido, observacoes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(id_cliente),
                    grau_esf_od.strip(),
                    grau_cil_od.strip() or "0.00",
                    eixo_od.strip() or "0°",
                    grau_esf_oe.strip(),
                    grau_cil_oe.strip() or "0.00",
                    eixo_oe.strip() or "0°",
                    adicao.strip() or "0.00",
                    dnp.strip(),
                    tipo_lente.strip(),
                    armacao.strip(),
                    float(valor_venda),
                    data_receita.strip(),
                    status_pedido.strip(),
                    observacoes.strip(),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            self._close_if_needed(conn)

    def listar_receitas_por_cliente(self, id_cliente: int) -> List[Dict[str, Any]]:
        """Retorna todas as receitas/vendas de um cliente específico."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM receitas
                WHERE id_cliente = ?
                ORDER BY id_receita DESC
                """,
                (int(id_cliente),),
            )
            return [dict(r) for r in cur.fetchall()]
        finally:
            self._close_if_needed(conn)

    def consultar_historico_completo(self, termo_busca: str = "") -> List[Dict[str, Any]]:
        """
        Retorna a junção (JOIN) de clientes com suas receitas para exibição rápida
        na Tela 3 de Consulta de Histórico (RF03 e RNF03).
        """
        termo = (termo_busca or "").strip()
        apenas_digitos = re.sub(r"\D", "", termo)
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            query_base = """
                SELECT
                    c.id_cliente,
                    c.nome,
                    c.cpf,
                    c.telefone,
                    c.data_nascimento,
                    c.endereco,
                    r.id_receita,
                    r.grau_esf_od,
                    r.grau_cil_od,
                    r.eixo_od,
                    r.grau_esf_oe,
                    r.grau_cil_oe,
                    r.eixo_oe,
                    r.adicao,
                    r.dnp,
                    r.tipo_lente,
                    r.armacao,
                    r.valor_venda,
                    r.data_receita,
                    r.status_pedido,
                    r.observacoes
                FROM clientes c
                LEFT JOIN receitas r ON c.id_cliente = r.id_cliente
            """
            if not termo:
                cur.execute(query_base + " ORDER BY c.nome ASC, r.id_receita DESC")
            else:
                like_term = f"%{termo}%"
                like_digits = f"%{apenas_digitos}%" if apenas_digitos else like_term
                cur.execute(
                    query_base
                    + """
                    WHERE c.nome LIKE ?
                       OR c.cpf LIKE ?
                       OR REPLACE(REPLACE(c.cpf, '.', ''), '-', '') LIKE ?
                       OR r.tipo_lente LIKE ?
                    ORDER BY c.nome ASC, r.id_receita DESC
                    """,
                    (like_term, like_term, like_digits, like_term),
                )
            return [dict(r) for r in cur.fetchall()]
        finally:
            self._close_if_needed(conn)
