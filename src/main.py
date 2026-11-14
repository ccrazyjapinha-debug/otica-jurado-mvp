"""
Ponto de entrada principal da aplicação Desktop - Ótica Jurado (MVP).

Pode ser executado via:
    python src/main.py
ou:
    python app.py
"""

from pathlib import Path
import sys
import tkinter as tk

# Garante que a raiz do projeto esteja no sys.path mesmo executando direto `python src/main.py`
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.database.db_manager import DatabaseManager
from src.services.auth_service import AuthService
from src.services.otica_service import OticaService
from src.ui.app_window import OticaAppWindow


def iniciar_aplicacao() -> None:
    """Inicializa as 3 camadas (Dados, Negócio e Apresentação) e abre a janela principal."""
    db_manager = DatabaseManager()
    auth_service = AuthService(db_manager)
    otica_service = OticaService(db_manager, auth_service)

    root = tk.Tk()
    OticaAppWindow(root, auth_service, otica_service)
    root.mainloop()


if __name__ == "__main__":
    iniciar_aplicacao()
