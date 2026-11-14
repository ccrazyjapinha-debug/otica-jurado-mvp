"""Atalho para execução direta dos testes automatizados na raiz do projeto."""

import unittest
from tests.test_otica import TestOticaJuradoMVP  # noqa: F401

if __name__ == "__main__":
    unittest.main(verbosity=2)
