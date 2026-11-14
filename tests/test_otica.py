"""
Suíte Completa de Testes Automatizados Unitários e de Integração - Ótica Jurado (MVP).

Cobre toda a matriz de rastreabilidade:
- RF01: Cadastro de Clientes e validação de campos obrigatórios.
- RF02: Registro de Receitas e Vendas Ópticas (dependência de id_cliente válido).
- RF03: Consulta rápida de histórico por Nome e CPF.
- RF04: Exportação de relatório CSV e emissão de orçamento/ficha para impressão.
- RNF01 (OWASP A07): Hashing criptográfico de senhas e autenticação.
- RNF02 (OWASP A01, A03, A05): Controle de acesso por sessão e proteção contra SQL Injection.
- RNF03: Teste de desempenho com 100 registros e mediana de 5 execuções < 2 segundos (2000 ms).
"""

import os
from pathlib import Path
import statistics
import sys
import tempfile
import unittest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.database.db_manager import DatabaseManager
from src.services.auth_service import AuthService
from src.services.otica_service import OticaService


class TestOticaJuradoMVP(unittest.TestCase):
    """Testes unitários e de integração da arquitetura em 3 camadas."""

    def setUp(self) -> None:
        self.db = DatabaseManager(db_path=":memory:")
        self.auth = AuthService(self.db)
        self.service = OticaService(self.db, self.auth)
        # Inicia sessão autenticada padrão para os testes operacionais
        self.auth.autenticar("gerente", "123456")

    def tearDown(self) -> None:
        self.db.close()

    def test_01_hash_senha_seguro_rnf01(self) -> None:
        """RNF01 / OWASP A07: Verifica que a senha nunca fica em texto limpo e valida o hash."""
        senha = "SenhaForte@2026"
        hash_gerado = AuthService.gerar_hash_senha(senha)
        self.assertNotEqual(senha, hash_gerado)
        self.assertTrue(AuthService.verificar_senha(senha, hash_gerado))
        self.assertFalse(AuthService.verificar_senha("SenhaErrada", hash_gerado))

    def test_02_controle_acesso_e_autenticacao_owasp_a01(self) -> None:
        """RNF01 / OWASP A01: Bloqueia operações caso o usuário não esteja autenticado."""
        self.auth.encerrar_sessao()
        self.assertFalse(self.auth.esta_autenticado())

        with self.assertRaises(PermissionError):
            self.service.buscar_historico_clientes("João")

        with self.assertRaises(ValueError):
            self.auth.autenticar("gerente", "senha_incorreta")

        usuario = self.auth.autenticar("gerente", "123456")
        self.assertEqual(usuario["username"], "gerente")
        self.assertTrue(self.auth.esta_autenticado())

    def test_03_cadastro_cliente_rf01(self) -> None:
        """RF01: Cadastra um novo cliente e formata automaticamente o CPF."""
        id_novo = self.service.cadastrar_cliente(
            nome="Carlos Eduardo Mendes",
            cpf="11122233344",
            telefone="(11) 98888-7777",
            data_nascimento="10/04/1990",
            endereco="Rua XV de Novembro, 50",
        )
        self.assertGreater(id_novo, 0)
        cli = self.db.buscar_cliente_por_id(id_novo)
        self.assertIsNotNone(cli)
        self.assertEqual(cli["cpf"], "111.222.333-44")

    def test_04_bloqueio_campos_obrigatorios_em_branco_rnf02(self) -> None:
        """RF01 / RNF02: Impede salvar cliente sem nome, sem telefone ou com CPF inválido."""
        with self.assertRaises(ValueError):
            self.service.cadastrar_cliente(nome="", cpf="11122233344", telefone="(11) 99999-0000")

        with self.assertRaises(ValueError):
            self.service.cadastrar_cliente(nome="Cliente Sem Telefone", cpf="11122233344", telefone="")

        with self.assertRaises(ValueError):
            self.service.cadastrar_cliente(nome="CPF Invalido", cpf="123", telefone="(11) 99999-0000")

    def test_05_registro_receita_e_venda_rf02(self) -> None:
        """RF02: Registra receita óptica completa (OD/OE e lente Crizal Acrílica)."""
        id_cli, id_rec = self.service.cadastrar_cliente_com_receita(
            nome="Beatriz Souza",
            cpf="55566677788",
            telefone="(11) 97777-6666",
            grau_esf_od="-2.50",
            grau_cil_od="-0.75",
            eixo_od="180°",
            grau_esf_oe="-2.00",
            grau_cil_oe="-0.50",
            eixo_oe="170°",
            adicao="+1.50",
            tipo_lente="Crizal Acrílica",
            valor_venda="750,00",
            data_receita="12/11/2026",
        )
        self.assertGreater(id_cli, 0)
        self.assertGreater(id_rec, 0)

        ficha = self.service.obter_ficha_completa_cliente(id_cli)
        self.assertEqual(len(ficha["receitas"]), 1)
        self.assertEqual(ficha["receitas"][0]["grau_esf_od"], "-2.50")
        self.assertEqual(ficha["receitas"][0]["tipo_lente"], "Crizal Acrílica")

    def test_06_dependencia_rf02_exige_cliente_valido(self) -> None:
        """Dependência RF02 -> RF01: Impede registrar receita para id_cliente inexistente."""
        with self.assertRaises(ValueError):
            self.service.registrar_receita(
                id_cliente=999999,
                grau_esf_od="-1.00",
                grau_esf_oe="-1.00",
                tipo_lente="Crizal Acrílica",
            )

    def test_07_protecao_sql_injection_owasp_a03(self) -> None:
        """RNF02 / OWASP A03: Garante que ataques de SQL Injection na busca são neutralizados."""
        payload_malicioso = "' OR '1'='1'; DROP TABLE clientes; --"
        resultados, _ = self.service.buscar_historico_clientes(payload_malicioso)
        self.assertEqual(len(resultados), 0)
        # Confirma que a tabela clientes continua intacta
        self.assertGreaterEqual(self.db.contar_clientes(), 4)

    def test_08_desempenho_consulta_100_registros_rnf03(self) -> None:
        """
        RNF03: Popula o banco com 100 registros e mede 5 execuções consecutivas,
        verificando se a mediana do tempo de resposta é inferior a 2000 ms (2 segundos).
        """
        for i in range(100):
            cpf_num = f"{10000000000 + i:011d}"
            self.service.cadastrar_cliente_com_receita(
                nome=f"Cliente Teste Desempenho {i:03d}",
                cpf=cpf_num,
                telefone="(11) 91111-2222",
                grau_esf_od="-1.25",
                grau_esf_oe="-1.50",
                tipo_lente="Crizal Acrílica",
                data_receita="11/11/2026",
            )

        tempos = []
        for _ in range(5):
            registros, tempo_ms = self.service.buscar_historico_clientes("Cliente Teste")
            self.assertGreaterEqual(len(registros), 100)
            tempos.append(tempo_ms)

        mediana_ms = statistics.median(tempos)
        self.assertLess(
            mediana_ms,
            2000.0,
            f"A mediana de busca ({mediana_ms:.2f} ms) ultrapassou o limite de 2000 ms do RNF03.",
        )

    def test_09_exportacao_relatorio_csv_rf04(self) -> None:
        """RF04: Testa a exportação dos registros para arquivo CSV externo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            caminho_csv = os.path.join(tmpdir, "teste_exportacao.csv")
            gerado = self.service.exportar_relatorio_csv(caminho_csv)
            self.assertTrue(os.path.exists(gerado))
            with open(gerado, "r", encoding="utf-8-sig") as f:
                conteudo = f.read()
            self.assertIn("João da Silva", conteudo)
            self.assertIn("Crizal Acrílica", conteudo)

    def test_10_emissao_orcamento_e_ficha_txt(self) -> None:
        """Valida a emissão de ficha/orçamento em texto (feedback da validação comunitária)."""
        cli = self.db.buscar_cliente_por_cpf("479.290.358-08")
        self.assertIsNotNone(cli)
        texto = self.service.gerar_orcamento_txt(cli["id_cliente"])
        self.assertIn("ÓTICA JURADO - FICHA E ORÇAMENTO", texto)
        self.assertIn("João da Silva", texto)
        self.assertIn("Crizal Acrílica", texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
