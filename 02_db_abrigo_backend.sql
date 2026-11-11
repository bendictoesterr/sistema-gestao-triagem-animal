-- =====================================================================
-- BANCO 2 — BACKEND DO PROJETO (Sistema de Gestão de Abrigo e Triagem Animal)
-- Modelo ER: abrigo_origens (1) —classifica— (N) animais (1) —possui— (0..1) adocoes
--
-- Este script é idempotente: pode ser executado várias vezes, sempre
-- recria as tabelas e carrega os mesmos dados de exemplo (sem duplicar).
-- =====================================================================

CREATE DATABASE IF NOT EXISTS db_abrigo_backend
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE db_abrigo_backend;

DROP VIEW  IF EXISTS vw_adocoes_realizadas;
DROP VIEW  IF EXISTS vw_painel_animais;
DROP TABLE IF EXISTS adocoes;
DROP TABLE IF EXISTS animais;
DROP TABLE IF EXISTS abrigo_origens;

-- ---------------------------------------------------------------------
-- Tabelas
-- ---------------------------------------------------------------------
CREATE TABLE abrigo_origens (
    id_origem         INT          NOT NULL AUTO_INCREMENT,
    descricao_origem  VARCHAR(100) NOT NULL,
    nivel_prioridade  VARCHAR(20)  NOT NULL,
    PRIMARY KEY (id_origem),
    UNIQUE KEY uq_origem_descricao (descricao_origem),
    CONSTRAINT ck_origem_prioridade CHECK (nivel_prioridade IN ('Crítica', 'Alta', 'Média', 'Baixa'))
);

CREATE TABLE animais (
    id_animal       INT          NOT NULL AUTO_INCREMENT,
    nome            VARCHAR(100) NOT NULL,
    especie         VARCHAR(50)  NOT NULL,
    raca            VARCHAR(100),
    sexo            VARCHAR(20)  NOT NULL,
    castrado        BOOLEAN      NOT NULL DEFAULT FALSE,
    condicao_saude  VARCHAR(50)  NOT NULL,
    status_adocao   VARCHAR(30)  NOT NULL DEFAULT 'Disponível',
    data_entrada    DATE         NOT NULL,
    id_origem       INT          NOT NULL,
    PRIMARY KEY (id_animal),
    -- Uma origem não pode ser apagada enquanto houver animais ligados a ela
    CONSTRAINT fk_animais_origem FOREIGN KEY (id_origem)
        REFERENCES abrigo_origens (id_origem) ON DELETE RESTRICT,
    CONSTRAINT ck_animais_sexo   CHECK (sexo IN ('Male', 'Female', 'Unknown')),
    CONSTRAINT ck_animais_saude  CHECK (condicao_saude IN ('Normal', 'Injured', 'Sick', 'Neonate')),
    CONSTRAINT ck_animais_status CHECK (status_adocao IN ('Disponível', 'Em Tratamento', 'Adotado'))
);

CREATE TABLE adocoes (
    id_adocao          INT          NOT NULL AUTO_INCREMENT,
    id_animal          INT          NOT NULL,
    nome_adotante      VARCHAR(120) NOT NULL,
    telefone_adotante  VARCHAR(30),
    data_adocao        DATE         NOT NULL,
    PRIMARY KEY (id_adocao),
    -- UNIQUE garante a cardinalidade 1:0..1 (cada animal tem no máximo uma adoção)
    UNIQUE KEY uq_adocao_animal (id_animal),
    -- Se o animal for excluído, o registro de adoção dele também é (não faz sentido sem o animal)
    CONSTRAINT fk_adocoes_animal FOREIGN KEY (id_animal)
        REFERENCES animais (id_animal) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- Views
-- ---------------------------------------------------------------------
-- Painel principal: animais + origem + prioridade, com castração legível
CREATE VIEW vw_painel_animais AS
SELECT
    a.id_animal,
    a.nome,
    a.especie,
    a.raca,
    a.sexo,
    CASE WHEN a.castrado = 1 THEN 'Sim' ELSE 'Não' END AS castrado_fmt,
    a.condicao_saude,
    a.status_adocao,
    a.data_entrada,
    o.descricao_origem AS canal_origem,
    o.nivel_prioridade
FROM animais a
JOIN abrigo_origens o ON o.id_origem = a.id_origem;

-- Adoções concluídas: animal + adotante
CREATE VIEW vw_adocoes_realizadas AS
SELECT
    d.id_adocao,
    a.id_animal,
    a.nome AS animal,
    a.especie,
    d.nome_adotante,
    d.telefone_adotante,
    d.data_adocao
FROM adocoes d
JOIN animais a ON a.id_animal = d.id_animal;

-- ---------------------------------------------------------------------
-- Dados de exemplo (fictícios)
-- ---------------------------------------------------------------------
-- A prioridade de cada origem segue a taxa de casos críticos de saúde observada
-- no banco de análise (>= 25% Crítica | >= 10% Alta | >= 2,5% Média | demais Baixa)
INSERT INTO abrigo_origens (id_origem, descricao_origem, nivel_prioridade) VALUES
    (1, 'Stray (Rua / Perdido)',                          'Média'),
    (2, 'ACO - Impound (Resgate Oficial)',                'Alta'),
    (3, 'Ambulance (Emergência Veterinária)',             'Crítica'),
    (4, 'Owner Surrender (Entrega pelo Tutor)',           'Baixa'),
    (5, 'Community Animal - Program (Programa Comunitário)', 'Baixa'),
    (6, 'Returns (Devolução de Adoção)',                  'Média'),
    (7, 'Agency (Transferência de Órgão Parceiro)',       'Baixa'),
    (8, 'ACO - Owner Surrender (Entrega ao Agente)',      'Média');

INSERT INTO animais (id_animal, nome, especie, raca, sexo, castrado, condicao_saude, status_adocao, data_entrada, id_origem) VALUES
    (1, 'Thor', 'Dog',    'German Shepherd',     'Male',   FALSE, 'Normal',  'Disponível',    '2026-11-01', 2),
    (2, 'Luna', 'Cat',    'Domestic Shorthair',  'Female', TRUE,  'Normal',  'Disponível',    '2026-11-02', 1),
    (3, 'Max',  'Puppy',  'Jack Russell Terrier','Male',   FALSE, 'Injured', 'Em Tratamento', '2026-11-03', 3),
    (4, 'Milo', 'Cat',    'Siamese',             'Male',   FALSE, 'Sick',    'Em Tratamento', '2026-11-03', 4),
    (5, 'Bela', 'Dog',    'Labrador Retriever',  'Female', TRUE,  'Normal',  'Adotado',       '2026-10-25', 1),
    (6, 'Nina', 'Kitten', 'Domestic Shorthair',  'Female', FALSE, 'Normal',  'Disponível',    '2026-11-04', 5);

INSERT INTO adocoes (id_animal, nome_adotante, telefone_adotante, data_adocao) VALUES
    (5, 'Mariana Souza', '(84) 90000-0001', '2026-11-05');
