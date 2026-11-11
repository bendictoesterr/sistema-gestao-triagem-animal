# Sistema de Gestão de Abrigo e Triagem Animal — BD, Unidade 2

Dois bancos MySQL + dashboard em Streamlit:

| Banco | Para quê | Onde é criado |
|---|---|---|
| `db_analise_publica` | Análise dos dados públicos do Austin Animal Center (tabela `intakes_raw` + view `vw_intakes_limpo`) | `sql/01_db_analise_publica.sql` + `importar_csv.py` |
| `db_abrigo_backend` | Backend do sistema (`abrigo_origens`, `animais`, `adocoes`, views `vw_painel_animais` e `vw_adocoes_realizadas`) | `sql/02_db_abrigo_backend.sql` |

## Como rodar (primeira vez)

Pré-requisitos: Docker Desktop aberto, Python 3.10+.

```bash
# 1. Sobe o MySQL (já cria os dois bancos e carrega os dados de exemplo do abrigo)
docker compose up -d

# 2. Dependências do Python
pip install -r requirements.txt

# 3. Importa o CSV (aguarde a mensagem "Sucesso! 19178 linhas ...")
python importar_csv.py

# 4. Dashboard
streamlit run app.py
```

Conexão no MySQL Workbench / extensão SQL do VS Code: host `127.0.0.1`, porta `3306`, usuário `root`, senha `root`.

## Dia a dia

- **Ligar/desligar:** `docker compose up -d` / `docker compose stop` (os dados ficam guardados no volume).
- **Resetar só o backend** (volta aos 6 animais de exemplo, sem duplicatas): abra `sql/02_db_abrigo_backend.sql` no Workbench e execute o script inteiro.
- **Resetar tudo** (apaga os dois bancos e recria): `docker compose down -v`, depois repita os passos 1 e 3.
- **Consultas da análise:** `consultas/03_consultas_analise.sql` (rode bloco por bloco).

## Problemas comuns

- **"Can't connect to MySQL server" no app:** o contêiner não está de pé. Rode `docker compose up -d` e espere uns 20 s (`docker compose ps` deve mostrar `healthy`).
- **Porta 3306 ocupada** (MySQL instalado no Windows ou outro contêiner): use outra porta, por exemplo `DB_PORT=3307 docker compose up -d`, e defina a mesma variável `DB_PORT` antes de rodar `importar_csv.py` e `streamlit run app.py`. No PowerShell: `$env:DB_PORT=3307`.
- **Já tenho um contêiner MySQL rodando:** não precisa de outro. Execute `sql/01_db_analise_publica.sql` e `sql/02_db_abrigo_backend.sql` no Workbench e siga a partir do passo 2.
- **Os scripts de `sql/` não rodaram:** eles só executam quando o volume é criado. Use `docker compose down -v` e suba de novo.

## Variáveis de ambiente (opcionais)

`DB_HOST` (127.0.0.1), `DB_PORT` (3306), `DB_USER` (root), `DB_PASSWORD` (root). A senha `root` é só para o contêiner local de desenvolvimento; ao publicar no GitHub, não inclua senhas reais.

## Estrutura

```
docker-compose.yml          MySQL 8 com init automático
sql/                        scripts de criação (rodam no 1º start do contêiner)
consultas/                  consultas de análise (para o relatório e a apresentação)
importar_csv.py             CSV -> db_analise_publica.intakes_raw
app.py                      dashboard (Streamlit) integrado aos dois bancos
Austin_Animal_Center_Intakes_20261104.csv   dados públicos
```
