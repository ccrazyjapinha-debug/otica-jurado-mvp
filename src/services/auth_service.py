"""
Serviço de Autenticação e Controle de Sessão (RNF01 e RNF02 - OWASP Top 10).

Atende:
- OWASP A07:2021 (Identification and Authentication Failures): Senhas armazenadas
  exclusivamente com hash criptográfico forte e salt (bcrypt ou PBKDF2-HMAC-SHA256),
  nunca em texto limpo, MD5 ou SHA-1.
- OWASP A01:2021 (Broken Access Control): Controle de sessão ativa antes de
  permitir operações nas camadas de negócio e interface.
"""

import hashlib
import hmac
import secrets
from typing import Dict, Optional

try:
    import bcrypt  # type: ignore
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False


class AuthService:
    """Gerencia hashing seguro de credenciais, login e estado da sessão."""

    PBKDF2_ITERATIONS = 260_000

    def __init__(self, db_manager) -> None:
        self.db = db_manager
        self._usuario_logado: Optional[Dict[str, str]] = None

    @classmethod
    def gerar_hash_senha(cls, senha_plana: str) -> str:
        """
        Gera um hash seguro para a senha informada (RNF01).
        Usa bcrypt se disponível no ambiente, ou PBKDF2-HMAC-SHA256 (padrão NIST/OWASP)
        da biblioteca nativa do Python.
        """
        if not senha_plana or len(senha_plana.strip()) < 4:
            raise ValueError("A senha deve conter pelo menos 4 caracteres.")

        if HAS_BCRYPT:
            salt = bcrypt.gensalt(rounds=12)
            hashed = bcrypt.hashpw(senha_plana.encode("utf-8"), salt)
            return hashed.decode("utf-8")

        salt_hex = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            senha_plana.encode("utf-8"),
            bytes.fromhex(salt_hex),
            cls.PBKDF2_ITERATIONS,
        )
        return f"pbkdf2_sha256${cls.PBKDF2_ITERATIONS}${salt_hex}${dk.hex()}"

    @classmethod
    def verificar_senha(cls, senha_plana: str, senha_hash: str) -> bool:
        """Verifica de forma segura (constant-time) se a senha corresponde ao hash."""
        if not senha_plana or not senha_hash:
            return False

        if senha_hash.startswith("$2b$") or senha_hash.startswith("$2a$"):
            if not HAS_BCRYPT:
                return False
            return bool(
                bcrypt.checkpw(
                    senha_plana.encode("utf-8"),
                    senha_hash.encode("utf-8"),
                )
            )

        if senha_hash.startswith("pbkdf2_sha256$"):
            try:
                _, iter_str, salt_hex, hash_hex = senha_hash.split("$", 3)
                iterations = int(iter_str)
                dk = hashlib.pbkdf2_hmac(
                    "sha256",
                    senha_plana.encode("utf-8"),
                    bytes.fromhex(salt_hex),
                    iterations,
                )
                return hmac.compare_digest(dk.hex(), hash_hex)
            except (ValueError, TypeError):
                return False

        return False

    def autenticar(self, username: str, senha_plana: str) -> Dict[str, str]:
        """
        Valida credenciais do usuário no banco de dados e inicia a sessão (RNF01).
        Retorna os dados públicos do usuário autenticado ou levanta ValueError amigável.
        """
        user_clean = (username or "").strip().lower()
        if not user_clean or not senha_plana:
            raise ValueError("Informe o usuário e a senha para acessar o sistema.")

        registro = self.db.buscar_usuario_por_username(user_clean)
        if not registro:
            raise ValueError("Usuário ou senha inválidos. Verifique suas credenciais.")

        if not self.verificar_senha(senha_plana, registro["senha_hash"]):
            raise ValueError("Usuário ou senha inválidos. Verifique suas credenciais.")

        self._usuario_logado = {
            "id_usuario": str(registro["id_usuario"]),
            "username": registro["username"],
            "nome_exibicao": registro["nome_exibicao"],
            "papel": registro["papel"],
        }
        return self._usuario_logado

    def esta_autenticado(self) -> bool:
        """Retorna True se houver uma sessão válida ativa (OWASP A01:2021)."""
        return self._usuario_logado is not None

    @property
    def usuario_atual(self) -> Optional[Dict[str, str]]:
        """Retorna os dados do usuário logado na sessão atual."""
        return self._usuario_logado

    def encerrar_sessao(self) -> None:
        """Encerra a sessão ativa (Logout)."""
        self._usuario_logado = None
