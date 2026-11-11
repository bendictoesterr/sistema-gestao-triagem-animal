"""Importa o CSV do Austin Animal Center para db_analise_publica.intakes_raw.

Pré-requisito: contêiner de pé (docker compose up -d), que já cria o banco e a tabela.
Pode ser executado mais de uma vez: INSERT IGNORE + chave primária (id) evitam duplicatas.
"""
import os
import sys
from pathlib import Path

import mysql.connector
import pandas as pd

CSV = Path(__file__).parent / "Austin_Animal_Center_Intakes_20261104.csv"

if not CSV.exists():
    sys.exit(f"CSV não encontrado: {CSV}. Coloque o arquivo na mesma pasta deste script.")

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", "root"),
    database="db_analise_publica",
)
cursor = conn.cursor()

# Lê o CSV
df = pd.read_csv(CSV)
df["IsPreviouslySpayedNeutered"] = df["IsPreviouslySpayedNeutered"].astype(str)  # 'True' / 'False'

# Converte para object ANTES de trocar NaN por None (evita que o Pandas recrie float('nan'))
df = df.astype(object).where(pd.notnull(df), None)
dados = df.values.tolist()

sql = "INSERT IGNORE INTO intakes_raw VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

# Insere em lotes de 5000 para evitar estouro de pacote no MySQL
for i in range(0, len(dados), 5000):
    cursor.executemany(sql, dados[i:i + 5000])
    conn.commit()

cursor.execute("SELECT COUNT(*) FROM intakes_raw")
total = cursor.fetchone()[0]
print(f"Sucesso! {total} linhas presentes na tabela db_analise_publica.intakes_raw (CSV tem {len(df)}).")

cursor.close()
conn.close()
