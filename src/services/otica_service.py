"""
Camada de Regras de Negócio - Sistema de Gestão Ótica Jurado (MVP).

Atende aos Requisitos:
- RF01: Cadastro e validação de clientes (nome, CPF, telefone obrigatórios).
- RF02: Registro de receitas ópticas e vendas (OD/OE, tipo de lente, armação, valor, data).
- RF03: Consulta rápida por Nome ou CPF com medição de tempo (< 2 segundos - RNF03).
- RF04: Exportação de relatórios (CSV) e emissão de ficha/orçamento para impressão (TXT).
- RNF02 (OWASP A01/A03/A05): Controle de acesso por sessão, sanitização e mensagens amigáveis.
"""

import csv
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class OticaService:
    """Regras de negócio para gestão de clientes, receitas ópticas e relatórios."""

    def __init__(self, db_manager, auth_service=None) -> None:
        self.db = db_manager
        self.auth = auth_service

    def _exigir_autenticacao(self) -> None:
        """Verifica se há sessão ativa quando o serviço de autenticação está acoplado (OWASP A01)."""
        if self.auth is not None and not self.auth.esta_autenticado():
            raise PermissionError("Acesso negado: realize o login antes de executar esta operação.")

    @staticmethod
    def formatar_cpf(cpf: str) -> str:
        """Valida e formata o CPF no padrão XXX.XXX.XXX-XX."""
        digitos = re.sub(r"\D", "", cpf or "")
        if len(digitos) != 11:
            raise ValueError("O CPF deve conter exatamente 11 dígitos numéricos.")
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"

    @staticmethod
    def validar_grau_optico(valor_grau: str, nome_campo: str, obrigatorio: bool = True) -> str:
        """Valida se a dioptria informada (ex: -2.25, +1.50, 0.00) é um número válido."""
        texto = (valor_grau or "").strip().replace(",", ".")
        if not texto:
            if obrigatorio:
                raise ValueError(f"O campo '{nome_campo}' é obrigatório.")
            return "0.00"
        try:
            num = float(texto)
        except ValueError as exc:
            raise ValueError(
                f"Valor inválido em '{nome_campo}': informe um grau numérico (ex: -2.25 ou +1.50)."
            ) from exc

        if num < -30.0 or num > 30.0:
            raise ValueError(f"O grau informado em '{nome_campo}' ({num:+.2f}) está fora da faixa óptica (-30 a +30).")

        if num > 0:
            return f"+{num:.2f}"
        if num == 0:
            return "0.00"
        return f"{num:.2f}"

    def cadastrar_cliente(
        self,
        nome: str,
        cpf: str,
        telefone: str,
        data_nascimento: str = "",
        endereco: str = "",
    ) -> int:
        """Valida os dados obrigatórios e cadastra um novo cliente (RF01)."""
        self._exigir_autenticacao()

        nome_limpo = (nome or "").strip()
        telefone_limpo = (telefone or "").strip()
        if len(nome_limpo) < 3:
            raise ValueError("O nome do cliente é obrigatório e deve ter pelo menos 3 letras.")
        if not telefone_limpo or len(re.sub(r"\D", "", telefone_limpo)) < 8:
            raise ValueError("O telefone do cliente é obrigatório (informe um número válido).")

        cpf_formatado = self.formatar_cpf(cpf)

        existente = self.db.buscar_cliente_por_cpf(cpf_formatado)
        if existente:
            raise ValueError(
                f"Já existe um cliente cadastrado com o CPF {cpf_formatado} ({existente['nome']})."
            )

        try:
            return self.db.inserir_cliente(
                nome=nome_limpo,
                cpf=cpf_formatado,
                telefone=telefone_limpo,
                data_nascimento=(data_nascimento or "").strip(),
                endereco=(endereco or "").strip(),
            )
        except sqlite3.Error as exc:
            raise RuntimeError("Não foi possível salvar o cliente no banco de dados local.") from exc

    def cadastrar_cliente_com_receita(
        self,
        nome: str,
        cpf: str,
        telefone: str,
        grau_esf_od: str,
        grau_esf_oe: str,
        tipo_lente: str,
        data_receita: str = "",
        data_nascimento: str = "",
        endereco: str = "",
        grau_cil_od: str = "0.00",
        eixo_od: str = "0°",
        grau_cil_oe: str = "0.00",
        eixo_oe: str = "0°",
        adicao: str = "0.00",
        dnp: str = "",
        armacao: str = "",
        valor_venda: str = "0.00",
        status_pedido: str = "Pedido Entregue / Concluído",
        observacoes: str = "",
    ) -> Tuple[int, int]:
        """
        Fluxo integrado da Tela 2 (RF01 + RF02):
        Se o cliente já existir pelo CPF, atualiza seus dados básicos e adiciona a nova receita;
        caso contrário, cria o cliente e vincula a receita óptica.
        """
        self._exigir_autenticacao()

        nome_limpo = (nome or "").strip()
        telefone_limpo = (telefone or "").strip()
        if len(nome_limpo) < 3:
            raise ValueError("O campo 'Nome do Cliente' é obrigatório.")
        if not telefone_limpo or len(re.sub(r"\D", "", telefone_limpo)) < 8:
            raise ValueError("O campo 'Telefone' é obrigatório.")

        cpf_formatado = self.formatar_cpf(cpf)

        # Valida todos os campos da receita antes de gravar o cliente
        esf_od = self.validar_grau_optico(grau_esf_od, "Grau Esférico OD", obrigatorio=True)
        esf_oe = self.validar_grau_optico(grau_esf_oe, "Grau Esférico OE", obrigatorio=True)
        cil_od = self.validar_grau_optico(grau_cil_od, "Grau Cilíndrico OD", obrigatorio=False)
        cil_oe = self.validar_grau_optico(grau_cil_oe, "Grau Cilíndrico OE", obrigatorio=False)
        add_val = self.validar_grau_optico(adicao, "Adição", obrigatorio=False)

        lente_limpa = (tipo_lente or "").strip()
        if not lente_limpa:
            raise ValueError("O campo 'Tipo de Lente' é obrigatório (ex: Crizal Acrílica).")

        data_final = (data_receita or "").strip() or datetime.now().strftime("%d/%m/%Y")

        valor_str = ( str(valor_venda) if valor_venda is not None else "0" ).strip().replace("R$", "").replace(" ", "").replace(",", ".")
        try:
            valor_float = float(valor_str) if valor_str else 0.0
            if valor_float < 0:
                raise ValueError
        except ValueError as exc:
            raise ValueError("O campo 'Valor da Venda' deve conter um número positivo.") from exc

        cliente_existente = self.db.buscar_cliente_por_cpf(cpf_formatado)
        if cliente_existente:
            id_cliente = int(cliente_existente["id_cliente"])
            self.db.atualizar_cliente(
                id_cliente=id_cliente,
                nome=nome_limpo,
                cpf=cpf_formatado,
                telefone=telefone_limpo,
                data_nascimento=(data_nascimento or cliente_existente.get("data_nascimento", "")).strip(),
                endereco=(endereco or cliente_existente.get("endereco", "")).strip(),
            )
        else:
            id_cliente = self.db.inserir_cliente(
                nome=nome_limpo,
                cpf=cpf_formatado,
                telefone=telefone_limpo,
                data_nascimento=(data_nascimento or "").strip(),
                endereco=(endereco or "").strip(),
            )

        id_receita = self.db.inserir_receita(
            id_cliente=id_cliente,
            grau_esf_od=esf_od,
            grau_cil_od=cil_od,
            eixo_od=(eixo_od or "0°").strip(),
            grau_esf_oe=esf_oe,
            grau_cil_oe=cil_oe,
            eixo_oe=(eixo_oe or "0°").strip(),
            adicao=add_val,
            dnp=(dnp or "").strip(),
            tipo_lente=lente_limpa,
            armacao=(armacao or "").strip(),
            valor_venda=valor_float,
            data_receita=data_final,
            status_pedido=(status_pedido or "Pedido Entregue / Concluído").strip(),
            observacoes=(observacoes or "").strip(),
        )
        return id_cliente, id_receita

    def registrar_receita(
        self,
        id_cliente: int,
        grau_esf_od: str,
        grau_esf_oe: str,
        tipo_lente: str,
        data_receita: str = "",
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
        """Registra uma receita óptica validando a existência prévia do cliente (Dependência RF02 -> RF01)."""
        self._exigir_autenticacao()

        cliente = self.db.buscar_cliente_por_id(id_cliente)
        if not cliente:
            raise ValueError("Cliente não encontrado. A receita deve estar vinculada a um cliente válido (RF01).")

        esf_od = self.validar_grau_optico(grau_esf_od, "Grau Esférico OD", obrigatorio=True)
        esf_oe = self.validar_grau_optico(grau_esf_oe, "Grau Esférico OE", obrigatorio=True)
        cil_od = self.validar_grau_optico(grau_cil_od, "Grau Cilíndrico OD", obrigatorio=False)
        cil_oe = self.validar_grau_optico(grau_cil_oe, "Grau Cilíndrico OE", obrigatorio=False)
        add_val = self.validar_grau_optico(adicao, "Adição", obrigatorio=False)

        if not (tipo_lente or "").strip():
            raise ValueError("O tipo de lente é obrigatório.")

        data_final = (data_receita or "").strip() or datetime.now().strftime("%d/%m/%Y")

        return self.db.inserir_receita(
            id_cliente=id_cliente,
            grau_esf_od=esf_od,
            grau_cil_od=cil_od,
            eixo_od=eixo_od,
            grau_esf_oe=esf_oe,
            grau_cil_oe=cil_oe,
            eixo_oe=eixo_oe,
            adicao=add_val,
            dnp=dnp,
            tipo_lente=tipo_lente,
            armacao=armacao,
            valor_venda=float(valor_venda),
            data_receita=data_final,
            status_pedido=status_pedido,
            observacoes=observacoes,
        )

    def buscar_historico_clientes(self, termo_busca: str = "") -> Tuple[List[Dict[str, Any]], float]:
        """
        Executa a consulta de clientes e histórico de receitas (RF03)
        retornando a lista de registros e o tempo gasto em milissegundos (RNF03 < 2000 ms).
        """
        self._exigir_autenticacao()
        inicio = time.perf_counter()
        registros = self.db.consultar_historico_completo(termo_busca)
        tempo_ms = (time.perf_counter() - inicio) * 1000.0
        return registros, tempo_ms

    def obter_ficha_completa_cliente(self, id_cliente: int) -> Dict[str, Any]:
        """Retorna os dados cadastrais do cliente e todas as suas receitas/compras."""
        self._exigir_autenticacao()
        cliente = self.db.buscar_cliente_por_id(id_cliente)
        if not cliente:
            raise ValueError("Cliente não encontrado no sistema.")
        receitas = self.db.listar_receitas_por_cliente(id_cliente)
        return {
            "cliente": cliente,
            "receitas": receitas,
        }

    def exportar_relatorio_csv(self, caminho_arquivo: Optional[str] = None, termo_busca: str = "") -> str:
        """Exporta os registros consultados para um arquivo CSV estruturado (RF04)."""
        self._exigir_autenticacao()
        registros, _ = self.buscar_historico_clientes(termo_busca)

        if not caminho_arquivo:
            base_dir = Path(__file__).resolve().parent.parent.parent / "relatorios_exportados"
            base_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho_arquivo = str(base_dir / f"relatorio_otica_jurado_{timestamp}.csv")

        campos = [
            "id_cliente",
            "nome",
            "cpf",
            "telefone",
            "data_receita",
            "grau_esf_od",
            "grau_cil_od",
            "eixo_od",
            "grau_esf_oe",
            "grau_cil_oe",
            "eixo_oe",
            "adicao",
            "tipo_lente",
            "armacao",
            "valor_venda",
            "status_pedido",
        ]
        with open(caminho_arquivo, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore", delimiter=";")
            writer.writeheader()
            for reg in registros:
                writer.writerow(reg)

        return caminho_arquivo

    def gerar_orcamento_txt(self, id_cliente: int, caminho_arquivo: Optional[str] = None) -> str:
        """
        Gera um arquivo de Ficha Óptica / Comprovante de Orçamento pronto para impressão
        (Implementação da sugestão da comunidade nas rodadas de validação da Experiência Prática 3).
        """
        ficha = self.obter_ficha_completa_cliente(id_cliente)
        cli = ficha["cliente"]
        receitas = ficha["receitas"]

        linhas = [
            "================================================================",
            "                 ÓTICA JURADO - FICHA E ORÇAMENTO               ",
            "================================================================",
            f"Data de Emissão : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            f"Cliente         : {cli['nome']}",
            f"CPF             : {cli['cpf']}",
            f"Telefone        : {cli['telefone']}",
            f"Nascimento      : {cli.get('data_nascimento') or 'Não informado'}",
            f"Endereço        : {cli.get('endereco') or 'Não informado'}",
            "----------------------------------------------------------------",
            "             HISTÓRICO DE RECEITAS E COMPRAS ÓPTICAS            ",
            "----------------------------------------------------------------",
        ]

        if not receitas:
            linhas.append("Nenhuma receita óptica registrada para este cliente.")
        else:
            for idx, r in enumerate(receitas, start=1):
                valor_fmt = f"R$ {float(r.get('valor_venda') or 0.0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                linhas.extend(
                    [
                        f"[{idx}] Data da Compra/Receita: {r['data_receita']}  |  Status: {r['status_pedido']}",
                        f"    • Olho Direito (OD) : Esf {r['grau_esf_od']} | Cil {r['grau_cil_od']} | Eixo {r['eixo_od']}",
                        f"    • Olho Esquerdo (OE): Esf {r['grau_esf_oe']} | Cil {r['grau_cil_oe']} | Eixo {r['eixo_oe']}",
                        f"    • Adição: {r.get('adicao') or '0.00'}  |  DNP: {r.get('dnp') or 'Padrão'}",
                        f"    • Tipo de Lente     : {r['tipo_lente']}",
                        f"    • Armação           : {r.get('armacao') or 'Própria do Cliente'}",
                        f"    • Valor Total       : {valor_fmt}",
                        f"    • Observações       : {r.get('observacoes') or '-'}",
                        "----------------------------------------------------------------",
                    ]
                )

        linhas.append("Ótica Jurado — Qualidade e Precisão em Saúde Visual")
        linhas.append("================================================================")
        conteudo = "\n".join(linhas)

        if caminho_arquivo:
            with open(caminho_arquivo, mode="w", encoding="utf-8") as f:
                f.write(conteudo)

        return conteudo
