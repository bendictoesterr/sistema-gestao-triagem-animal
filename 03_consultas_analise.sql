-- =====================================================================
-- CONSULTAS DE ANÁLISE — db_analise_publica (Austin Animal Center Intakes)
-- Rode cada bloco separadamente no MySQL Workbench / extensão SQL do VS Code.
-- Consultas 1 a 3 são as mesmas dos prints já feitos; 4 a 6 são complementares.
-- =====================================================================
USE db_analise_publica;

-- ---------------------------------------------------------------------
-- Pergunta 0: a importação está completa?  (esperado: 19178)
-- ---------------------------------------------------------------------
SELECT COUNT(*) AS linhas_importadas FROM intakes_raw;

-- ---------------------------------------------------------------------
-- Consulta 1 — Quantos animais já chegam castrados, por tipo?  (SUM, AVG)
-- ---------------------------------------------------------------------
SELECT
    animal_type AS Tipo_Animal,
    COUNT(*) AS Total_Entradas,
    SUM(CASE WHEN is_previously_spayed_neutered = 'True' THEN 1 ELSE 0 END) AS Total_Castrados,
    SUM(CASE WHEN is_previously_spayed_neutered = 'False' THEN 1 ELSE 0 END) AS Total_Nao_Castrados,
    ROUND(AVG(CASE WHEN is_previously_spayed_neutered = 'True' THEN 100.0 ELSE 0.0 END), 2) AS Percentual_Castrados
FROM intakes_raw
GROUP BY animal_type
ORDER BY Total_Entradas DESC
LIMIT 10;

-- ---------------------------------------------------------------------
-- Consulta 2 — Qual o volume diário de entradas?  (COUNT, SUM, AVG, MAX, MIN)
-- Obs.: "Dias_Operacao" conta os dias em que houve ao menos uma entrada.
-- ---------------------------------------------------------------------
SELECT
    COUNT(dia) AS Dias_Operacao,
    SUM(qtd_diaria) AS Soma_Total_Entradas,
    ROUND(AVG(qtd_diaria), 2) AS Media_Entradas_Por_Dia,
    MAX(qtd_diaria) AS Pico_Maximo_Diario,
    MIN(qtd_diaria) AS Minimo_Diario
FROM (
    SELECT SUBSTRING(source_date, 1, 11) AS dia, COUNT(*) AS qtd_diaria
    FROM intakes_raw
    GROUP BY SUBSTRING(source_date, 1, 11)
) AS resumo_diario;

-- ---------------------------------------------------------------------
-- Consulta 3 — De onde vêm os animais e quantos chegam em estado crítico?
-- ---------------------------------------------------------------------
SELECT
    source_name AS Origem_Entrada,
    COUNT(*) AS Total_Casos,
    SUM(CASE WHEN intake_health_condition IN ('Injured', 'Sick', 'MED ATTN', 'MEDICAL') THEN 1 ELSE 0 END) AS Casos_Criticos_Saude
FROM intakes_raw
GROUP BY source_name
ORDER BY Total_Casos DESC
LIMIT 8;

-- ---------------------------------------------------------------------
-- Consulta 4 (complementar) — Taxa de casos críticos por origem
-- Liga a análise ao modelo: a taxa justifica o nivel_prioridade de abrigo_origens
-- (>= 25% Crítica | >= 10% Alta | >= 2,5% Média | demais Baixa)
-- ---------------------------------------------------------------------
SELECT
    source_name AS Origem_Entrada,
    COUNT(*) AS Total_Casos,
    SUM(CASE WHEN intake_health_condition IN ('Injured', 'Sick', 'MED ATTN', 'MEDICAL') THEN 1 ELSE 0 END) AS Casos_Criticos_Saude,
    ROUND(100.0 * SUM(CASE WHEN intake_health_condition IN ('Injured', 'Sick', 'MED ATTN', 'MEDICAL') THEN 1 ELSE 0 END) / COUNT(*), 2) AS Pct_Criticos
FROM intakes_raw
GROUP BY source_name
ORDER BY Total_Casos DESC
LIMIT 8;

-- ---------------------------------------------------------------------
-- Consulta 5 (complementar) — Castração agrupando filhotes com adultos
-- Usa a view vw_intakes_limpo (tipos corretos e categorias padronizadas)
-- ---------------------------------------------------------------------
SELECT
    especie_agrupada AS Especie,
    COUNT(*) AS Total_Entradas,
    SUM(castrado) AS Total_Castrados,
    ROUND(100.0 * SUM(castrado) / COUNT(*), 2) AS Percentual_Castrados
FROM vw_intakes_limpo
WHERE especie_agrupada IN ('Gato', 'Cão')
GROUP BY especie_agrupada;

-- ---------------------------------------------------------------------
-- Consulta 6 (complementar) — Qualidade dos dados: quanto da condição de saúde é preenchida?
-- Limitação a citar no relatório: a coluna é nula na maioria das entradas.
-- ---------------------------------------------------------------------
SELECT
    COUNT(*) AS Total_Entradas,
    SUM(CASE WHEN intake_health_condition IS NULL THEN 1 ELSE 0 END) AS Sem_Condicao_Registrada,
    ROUND(100.0 * SUM(CASE WHEN intake_health_condition IS NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS Pct_Sem_Condicao
FROM intakes_raw;
