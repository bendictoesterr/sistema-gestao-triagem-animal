-- =====================================================================
-- BANCO 1 — ANÁLISE DE DADOS PÚBLICOS
-- Fonte: Austin Animal Center Intakes (Portal de Dados Abertos de Austin, TX)
-- Arquivo: Austin_Animal_Center_Intakes_20261104.csv (19.178 linhas, 15 colunas)
--
-- Estratégia: a tabela intakes_raw guarda o CSV exatamente como veio
-- (tudo texto, para a importação nunca falhar). A view vw_intakes_limpo
-- aplica os tipos corretos (DATE, BOOLEAN) e padroniza categorias.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS db_analise_publica
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE db_analise_publica;

CREATE TABLE IF NOT EXISTS intakes_raw (
    id                              INT          NOT NULL,   -- ID do registro de entrada (único no CSV)
    source_date                     VARCHAR(30),             -- ex.: '2026 Nov 03 08:54:00 PM'
    animal_id                       INT,                     -- um mesmo animal pode ter várias entradas
    animal_type                     VARCHAR(50),             -- Cat, Dog, Kitten, Puppy, ...
    source_name                     VARCHAR(60),             -- origem da entrada (Stray, ACO - Impound, ...)
    name                            VARCHAR(100),
    is_previously_spayed_neutered   VARCHAR(5),              -- 'True' / 'False'
    sex                             VARCHAR(10),
    primary_breed                   VARCHAR(100),
    primary_color                   VARCHAR(50),
    secondary_color                 VARCHAR(50),
    intake_health_condition         VARCHAR(30),             -- Normal, Injured, Sick, ... (muitos NULL)
    date_of_birth                   VARCHAR(30),
    found_address                   VARCHAR(255),
    `timestamp`                     VARCHAR(30),
    PRIMARY KEY (id)
);

-- View com tipos corretos e categorias padronizadas (a tabela bruta não é alterada)
CREATE OR REPLACE VIEW vw_intakes_limpo AS
SELECT
    id,
    STR_TO_DATE(SUBSTRING(source_date, 1, 11), '%Y %b %d')  AS data_entrada,
    animal_id,
    animal_type,
    CASE
        WHEN animal_type IN ('Cat', 'Kitten') THEN 'Gato'
        WHEN animal_type IN ('Dog', 'Puppy')  THEN 'Cão'
        ELSE animal_type
    END                                                     AS especie_agrupada,
    source_name                                             AS origem,
    (is_previously_spayed_neutered = 'True')                AS castrado,
    CASE
        WHEN intake_health_condition = 'NEONATAL'                 THEN 'Neonate'
        WHEN intake_health_condition IN ('MED ATTN', 'MEDICAL')   THEN 'Medical'
        ELSE intake_health_condition
    END                                                     AS condicao_saude
FROM intakes_raw;
