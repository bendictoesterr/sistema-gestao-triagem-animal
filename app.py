import os
from datetime import date

import mysql.connector
import pandas as pd
import streamlit as st

st.set_page_config(page_title="PetShelter Manager - Dashboard", layout="wide")

# ---------------------------------------------------------------------
# Configuração (padrão = docker-compose.yml; pode ser trocada por variáveis de ambiente)
# ---------------------------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_BACKEND = "db_abrigo_backend"      # banco do sistema (CRUD)
DB_ANALISE = "db_analise_publica"     # banco de dados públicos (análise)

STATUS = ["Disponível", "Em Tratamento", "Adotado"]
CONDICOES = ["Normal", "Injured", "Sick", "Neonate"]


def get_conn(database=DB_BACKEND):
    return mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=database
    )


def run_query(query, params=None, fetch=True, db=DB_BACKEND):
    """Executa uma única instrução. SELECT devolve lista de dicts; demais fazem commit."""
    conn = get_conn(db)
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if fetch:
            return cursor.fetchall()
        conn.commit()
    finally:
        conn.close()


def run_transaction(operacoes, db=DB_BACKEND):
    """Executa várias instruções como UMA transação: ou todas valem, ou nenhuma."""
    conn = get_conn(db)
    try:
        cursor = conn.cursor()
        for query, params in operacoes:
            cursor.execute(query, params)
        conn.commit()
    except mysql.connector.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


def mostrar_tabela(df):
    """st.dataframe esticado na largura (compatível com versões novas e antigas do Streamlit)."""
    try:
        st.dataframe(df, width="stretch")
    except Exception:
        st.dataframe(df, use_container_width=True)


def flash(mensagem, tipo="success"):
    """Guarda uma mensagem para aparecer depois do st.rerun() (senão ela some)."""
    st.session_state["_flash"] = (tipo, mensagem)


def mostrar_flash():
    item = st.session_state.pop("_flash", None)
    if item:
        tipo, mensagem = item
        getattr(st, tipo)(mensagem)


st.title("🐾 Sistema de Gestão de Abrigo e Triagem Animal")
st.caption("Integração Frontend (Streamlit) + Backend Relacional (MySQL)")
mostrar_flash()

# ---------------------------------------------------------------------
# Métricas de topo (consulta agregada em tempo real)
# ---------------------------------------------------------------------
try:
    metricas = run_query("""
        SELECT
            COALESCE(SUM(CASE WHEN status_adocao <> 'Adotado' THEN 1 ELSE 0 END), 0)                  AS no_abrigo,
            COALESCE(SUM(CASE WHEN castrado = 0 AND status_adocao <> 'Adotado' THEN 1 ELSE 0 END), 0) AS nao_castrados,
            COALESCE(SUM(CASE WHEN status_adocao = 'Disponível' THEN 1 ELSE 0 END), 0)                AS disponiveis,
            COALESCE(SUM(CASE WHEN status_adocao = 'Adotado' THEN 1 ELSE 0 END), 0)                   AS adotados
        FROM animais
    """)[0]
except mysql.connector.Error as erro:
    st.error(
        f"Não foi possível conectar ao MySQL em {DB_HOST}:{DB_PORT} (banco `{DB_BACKEND}`): {erro}\n\n"
        "Verifique se o contêiner está de pé: `docker compose up -d` (pasta do projeto)."
    )
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Animais no Abrigo", int(metricas["no_abrigo"]))
c2.metric("Aguardando Castração", int(metricas["nao_castrados"]))
c3.metric("Disponíveis para Adoção", int(metricas["disponiveis"]))
c4.metric("Adotados", int(metricas["adotados"]))

st.divider()

lista_animais = run_query(
    "SELECT id_animal, nome, especie, status_adocao, condicao_saude, castrado FROM animais ORDER BY id_animal"
)
opcoes = {f"ID {a['id_animal']} - {a['nome']} ({a['especie']})": a for a in lista_animais}

aba_consulta, aba_inserir, aba_editar, aba_remover, aba_adocao, aba_analise = st.tabs([
    "🔍 1. Consultar (READ / View)",
    "➕ 2. Cadastrar (INSERT)",
    "✏️ 3. Atualizar (UPDATE)",
    "🗑️ 4. Remover (DELETE)",
    "🏠 5. Adotar (INSERT + UPDATE)",
    "📊 6. Análise (dados públicos)",
])

# ---------------------------------------------------------------------
# 1. READ — consulta via VIEW
# ---------------------------------------------------------------------
with aba_consulta:
    st.subheader("Animais Registrados (Dados consolidados via `vw_painel_animais`)")
    filtro_status = st.selectbox("Filtrar por Status:", ["Todos"] + STATUS)

    if filtro_status == "Todos":
        dados = run_query("SELECT * FROM vw_painel_animais ORDER BY id_animal DESC")
    else:
        dados = run_query(
            "SELECT * FROM vw_painel_animais WHERE status_adocao = %s ORDER BY id_animal DESC",
            (filtro_status,),
        )

    mostrar_tabela(pd.DataFrame(dados))

# ---------------------------------------------------------------------
# 2. CREATE — inserção
# ---------------------------------------------------------------------
with aba_inserir:
    st.subheader("Registrar Nova Entrada de Animal")
    origens = run_query("SELECT id_origem, descricao_origem FROM abrigo_origens ORDER BY id_origem")
    mapa_origens = {o["descricao_origem"]: o["id_origem"] for o in origens}

    with st.form("form_insert", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome do Animal", placeholder="Ex: Rex")
        especie = col2.selectbox("Espécie", ["Dog", "Cat", "Puppy", "Kitten", "Mammal"])
        raca = col1.text_input("Raça Principal", value="SRD / Mixed")
        sexo = col2.selectbox("Sexo", ["Male", "Female", "Unknown"])
        condicao = col1.selectbox("Condição de Saúde", CONDICOES)
        origem_nome = col2.selectbox("Canal de Origem", list(mapa_origens.keys()))
        castrado = st.checkbox("Animal já está castrado?")

        if st.form_submit_button("Cadastrar no MySQL"):
            if not nome.strip():
                st.warning("Informe o nome do animal.")
            else:
                try:
                    run_query(
                        """
                        INSERT INTO animais (nome, especie, raca, sexo, castrado, condicao_saude,
                                             status_adocao, data_entrada, id_origem)
                        VALUES (%s, %s, %s, %s, %s, %s, 'Disponível', %s, %s)
                        """,
                        (nome.strip(), especie, raca, sexo, castrado, condicao,
                         date.today(), mapa_origens[origem_nome]),
                        fetch=False,
                    )
                    flash(f"Animal '{nome.strip()}' inserido com sucesso!")
                    st.rerun()
                except mysql.connector.Error as erro:
                    st.error(f"Erro ao inserir no banco: {erro}")

# ---------------------------------------------------------------------
# 3. UPDATE — alteração
# ---------------------------------------------------------------------
with aba_editar:
    st.subheader("Atualizar Status, Castração ou Saúde")
    if not lista_animais:
        st.info("Nenhum animal cadastrado.")
    else:
        selecionado_label = st.selectbox("Selecione o registro para alterar:", list(opcoes.keys()))
        animal_atual = opcoes[selecionado_label]
        ja_adotado = animal_atual["status_adocao"] == "Adotado"

        # "Adotado" só é definido na aba 5 (que registra o adotante). Para um animal já adotado,
        # mudar para outro status significa devolvê-lo ao abrigo (a adoção é removida).
        status_opcoes = STATUS if ja_adotado else ["Disponível", "Em Tratamento"]
        if ja_adotado:
            st.caption("Este animal consta como adotado. Alterar o status para outro valor "
                       "o devolve ao abrigo e remove o registro de adoção.")
        else:
            st.caption("Para marcar um animal como adotado, use a aba 5 (assim o adotante é registrado).")

        id_animal = animal_atual["id_animal"]
        with st.form("form_update"):
            novo_status = st.selectbox(
                "Novo Status", status_opcoes,
                index=status_opcoes.index(animal_atual["status_adocao"]) if animal_atual["status_adocao"] in status_opcoes else 0,
                key=f"status_{id_animal}",
            )
            cond_atual = animal_atual["condicao_saude"]
            nova_condicao = st.selectbox(
                "Nova Condição de Saúde", CONDICOES,
                index=CONDICOES.index(cond_atual) if cond_atual in CONDICOES else 0,
                key=f"cond_{id_animal}",
            )
            novo_castrado = st.checkbox("Castrado", value=bool(animal_atual["castrado"]),
                                        key=f"cast_{id_animal}")

            if st.form_submit_button("Salvar Alterações"):
                operacoes = []
                if ja_adotado and novo_status != "Adotado":
                    operacoes.append(("DELETE FROM adocoes WHERE id_animal = %s", (id_animal,)))
                operacoes.append((
                    "UPDATE animais SET status_adocao = %s, condicao_saude = %s, castrado = %s "
                    "WHERE id_animal = %s",
                    (novo_status, nova_condicao, novo_castrado, id_animal),
                ))
                try:
                    run_transaction(operacoes)
                    flash("Registro atualizado com sucesso!")
                    st.rerun()
                except mysql.connector.Error as erro:
                    st.error(f"Erro ao atualizar: {erro}")

# ---------------------------------------------------------------------
# 4. DELETE — remoção (com confirmação)
# ---------------------------------------------------------------------
with aba_remover:
    st.subheader("Remover Registro de Animal")
    if not lista_animais:
        st.info("Nenhum animal cadastrado.")
    else:
        del_label = st.selectbox("Selecione o animal para excluir:", list(opcoes.keys()), key="del_select")
        animal_del = opcoes[del_label]
        if animal_del["status_adocao"] == "Adotado":
            st.warning("Este animal possui adoção registrada: o registro de adoção "
                       "também será apagado (ON DELETE CASCADE).")
        # A chave inclui o ID: a confirmação nunca "vaza" de um animal para outro
        confirmou = st.checkbox(f"Confirmo a exclusão permanente de {animal_del['nome']} "
                                f"(ID {animal_del['id_animal']})", key=f"del_confirma_{animal_del['id_animal']}")
        if st.button("Confirmar Exclusão Permanente", type="primary", disabled=not confirmou):
            try:
                run_query("DELETE FROM animais WHERE id_animal = %s", (animal_del["id_animal"],), fetch=False)
                flash(f"Registro ID {animal_del['id_animal']} ({animal_del['nome']}) removido do banco de dados.",
                      "warning")
                st.rerun()
            except mysql.connector.Error as erro:
                st.error(f"Erro ao remover: {erro}")

# ---------------------------------------------------------------------
# 5. Adoção — INSERT em adocoes + UPDATE em animais (mesma transação)
# ---------------------------------------------------------------------
with aba_adocao:
    st.subheader("Registrar Adoção")
    disponiveis = {k: v for k, v in opcoes.items() if v["status_adocao"] == "Disponível"}
    if not disponiveis:
        st.info("Nenhum animal disponível para adoção no momento.")
    else:
        with st.form("form_adocao", clear_on_submit=True):
            animal_label = st.selectbox("Animal disponível:", list(disponiveis.keys()))
            col1, col2 = st.columns(2)
            nome_adotante = col1.text_input("Nome do Adotante")
            telefone = col2.text_input("Telefone", placeholder="(84) 90000-0000")
            data_adocao = st.date_input("Data da adoção", value=date.today())

            if st.form_submit_button("Registrar Adoção"):
                if not nome_adotante.strip():
                    st.warning("Informe o nome do adotante.")
                else:
                    id_adotado = disponiveis[animal_label]["id_animal"]
                    try:
                        run_transaction([
                            ("INSERT INTO adocoes (id_animal, nome_adotante, telefone_adotante, data_adocao) "
                             "VALUES (%s, %s, %s, %s)",
                             (id_adotado, nome_adotante.strip(), telefone.strip() or None, data_adocao)),
                            ("UPDATE animais SET status_adocao = 'Adotado' WHERE id_animal = %s", (id_adotado,)),
                        ])
                        flash(f"Adoção registrada: {disponiveis[animal_label]['nome']} → {nome_adotante.strip()}.")
                        st.rerun()
                    except mysql.connector.Error as erro:
                        st.error(f"Erro ao registrar adoção: {erro}")

    st.markdown("#### Adoções realizadas (view `vw_adocoes_realizadas`)")
    adocoes = run_query("SELECT * FROM vw_adocoes_realizadas ORDER BY data_adocao DESC, id_adocao DESC")
    if adocoes:
        mostrar_tabela(pd.DataFrame(adocoes))
    else:
        st.caption("Nenhuma adoção registrada ainda.")

# ---------------------------------------------------------------------
# 6. Análise — dados públicos (Austin Animal Center), banco db_analise_publica
# ---------------------------------------------------------------------
with aba_analise:
    st.subheader("Análise dos Dados Públicos — Austin Animal Center (Intakes)")
    st.caption(f"Fonte: tabela `intakes_raw` do banco `{DB_ANALISE}`. As mesmas consultas estão em consultas/03_consultas_analise.sql.")
    try:
        resumo = run_query("""
            SELECT
                COUNT(dia) AS dias_operacao,
                SUM(qtd_diaria) AS total_entradas,
                ROUND(AVG(qtd_diaria), 2) AS media_dia,
                MAX(qtd_diaria) AS pico_diario,
                MIN(qtd_diaria) AS minimo_diario
            FROM (
                SELECT SUBSTRING(source_date, 1, 11) AS dia, COUNT(*) AS qtd_diaria
                FROM intakes_raw
                GROUP BY SUBSTRING(source_date, 1, 11)
            ) AS resumo_diario
        """, db=DB_ANALISE)[0]

        por_tipo = pd.DataFrame(run_query("""
            SELECT
                animal_type AS tipo_animal,
                COUNT(*) AS total_entradas,
                SUM(CASE WHEN is_previously_spayed_neutered = 'True' THEN 1 ELSE 0 END) AS castrados,
                SUM(CASE WHEN is_previously_spayed_neutered = 'False' THEN 1 ELSE 0 END) AS nao_castrados,
                ROUND(AVG(CASE WHEN is_previously_spayed_neutered = 'True' THEN 100.0 ELSE 0.0 END), 2) AS percentual_castrados
            FROM intakes_raw
            GROUP BY animal_type
            ORDER BY total_entradas DESC
            LIMIT 10
        """, db=DB_ANALISE))

        por_origem = pd.DataFrame(run_query("""
            SELECT
                source_name AS origem_entrada,
                COUNT(*) AS total_casos,
                SUM(CASE WHEN intake_health_condition IN ('Injured', 'Sick', 'MED ATTN', 'MEDICAL') THEN 1 ELSE 0 END) AS casos_criticos
            FROM intakes_raw
            GROUP BY source_name
            ORDER BY total_casos DESC
            LIMIT 8
        """, db=DB_ANALISE))
    except mysql.connector.Error as erro:
        st.error(f"Não foi possível ler `{DB_ANALISE}`: {erro}\n\n"
                 "Rode `python importar_csv.py` para carregar o CSV na tabela intakes_raw.")
    else:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Dias com entradas", int(resumo["dias_operacao"]))
        m2.metric("Total de entradas", f"{int(resumo['total_entradas']):,}".replace(",", "."))
        m3.metric("Média por dia", float(resumo["media_dia"]))
        m4.metric("Pico diário (MAX)", int(resumo["pico_diario"]))
        m5.metric("Mínimo diário (MIN)", int(resumo["minimo_diario"]))

        st.markdown("#### Percentual de animais que já chegam castrados, por tipo")
        por_tipo["percentual_castrados"] = por_tipo["percentual_castrados"].astype(float)
        st.bar_chart(por_tipo.set_index("tipo_animal")["percentual_castrados"])
        mostrar_tabela(por_tipo)

        st.markdown("#### Casos críticos de saúde por origem da entrada")
        por_origem["total_casos"] = por_origem["total_casos"].astype(int)
        por_origem["casos_criticos"] = por_origem["casos_criticos"].astype(int)
        por_origem["pct_criticos"] = (100 * por_origem["casos_criticos"] / por_origem["total_casos"]).round(2)
        st.bar_chart(por_origem.set_index("origem_entrada")["pct_criticos"])
        st.caption("Crítico = condição de saúde Injured, Sick, MED ATTN ou MEDICAL. "
                   "A origem 'Ambulance' concentra a maior taxa — por isso recebe prioridade Crítica no modelo do abrigo.")
        mostrar_tabela(por_origem)
