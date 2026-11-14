-- ============================================================================
-- Sistema de Gestão - Ótica Jurado (MVP)
-- Script DDL MySQL (Modelagem Relacional e Índices de Desempenho RNF03)
-- ============================================================================

CREATE DATABASE IF NOT EXISTS otica_jurado
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE otica_jurado;

-- 1. Tabela de Usuários (RNF01 - Autenticação Segura com Hash Robusto)
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    nome_exibicao VARCHAR(100) NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    papel VARCHAR(50) DEFAULT 'Gestora',
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. Entidade Clientes (RF01 - Cadastro de Clientes)
CREATE TABLE IF NOT EXISTS clientes (
    id_cliente INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(120) NOT NULL,
    cpf VARCHAR(20) NOT NULL UNIQUE,
    telefone VARCHAR(30) NOT NULL,
    data_nascimento VARCHAR(15) NULL,
    endereco VARCHAR(255) NULL,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Índices para garantir consulta rápida em menos de 2 segundos (RNF03)
CREATE INDEX idx_clientes_nome ON clientes(nome);
CREATE INDEX idx_clientes_cpf ON clientes(cpf);

-- 3. Entidade Receitas e Vendas Ópticas (RF02 - Histórico de Lentes e Dioptrias)
CREATE TABLE IF NOT EXISTS receitas (
    id_receita INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    grau_esf_od VARCHAR(20) NOT NULL,
    grau_cil_od VARCHAR(20) DEFAULT '0.00',
    eixo_od VARCHAR(10) DEFAULT '0°',
    grau_esf_oe VARCHAR(20) NOT NULL,
    grau_cil_oe VARCHAR(20) DEFAULT '0.00',
    eixo_oe VARCHAR(10) DEFAULT '0°',
    adicao VARCHAR(20) DEFAULT '0.00',
    dnp VARCHAR(25) DEFAULT '',
    tipo_lente VARCHAR(120) NOT NULL,
    armacao VARCHAR(120) DEFAULT '',
    valor_venda DECIMAL(10, 2) DEFAULT 0.00,
    data_receita VARCHAR(20) NOT NULL,
    status_pedido VARCHAR(60) DEFAULT 'Pedido Entregue / Concluído',
    observacoes TEXT NULL,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_receitas_cliente
        FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_receitas_cliente ON receitas(id_cliente);
CREATE INDEX idx_receitas_data ON receitas(data_receita);
