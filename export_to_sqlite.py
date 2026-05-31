#!/usr/bin/env python3
"""
Exportador - SINAPI + SEINFRA-CE para SQLite portátil
=====================================================
Extrai dados dos bancos MariaDB (via socket Unix) e grava
um único arquivo SQLite em /home/treta/dashboards/precos_portatil/dados.sqlite

Filtros aplicados:
  - SINAPI: apenas UF=CE e tipo_desoneracao=SEM
  - SEINFRA: todos os registros (já filtrados por versão 028)

Uso: python3 export_to_sqlite.py
"""

import sqlite3
import mysql.connector
import os
import sys
import time

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
SOCKET_PATH = "/tmp/sinapi_mysql.sock"
DB_USER = "treta"
DB_PASSWORD = ""
DB_SINAPI = "sinapi_2026_04"
DB_SEINFRA = "seinfra_ce_028"

OUTPUT_DIR = "/home/treta/dashboards/precos_portatil"
OUTPUT_DB = os.path.join(OUTPUT_DIR, "dados.sqlite")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_mysql(database):
    """Retorna conexão MariaDB."""
    return mysql.connector.connect(
        unix_socket=SOCKET_PATH,
        user=DB_USER,
        password=DB_PASSWORD,
        database=database,
        charset="utf8mb4",
        use_pure=True,
    )


def fetch_all(conn, sql, params=None):
    """Executa query e retorna todas as linhas como dicionários."""
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cur.close()
    return rows


def create_sqlite_table(cursor, name, columns, indexes=None):
    """Cria tabela no SQLite com colunas e índices."""
    cursor.execute(f"DROP TABLE IF EXISTS {name}")
    cursor.execute(f"CREATE TABLE {name} ({', '.join(columns)})")
    if indexes:
        for idx_name, idx_cols in indexes:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {name} ({idx_cols})")


def to_float(val):
    """Converte Decimal/None para float (ou None)."""
    if val is None:
        return None
    return float(val)

def progress(msg, current, total):
    """Mostra barra de progresso simples."""
    pct = min(current / total * 100, 100) if total else 100
    bar = "=" * int(pct / 2) + ">" + " " * (50 - int(pct / 2))
    sys.stdout.write(f"\r  {msg}  [{bar}] {current}/{total}  {pct:.0f}%")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("  Exportador SINAPI + SEINFRA → SQLite portátil")
    print("  Destino:", OUTPUT_DB)
    print("=" * 60)

    # Remove SQLite anterior
    if os.path.exists(OUTPUT_DB):
        os.remove(OUTPUT_DB)
        print("  SQLite anterior removido.")

    sq = sqlite3.connect(OUTPUT_DB)
    sq.execute("PRAGMA journal_mode=WAL")
    sq.execute("PRAGMA synchronous=OFF")
    sq.execute("PRAGMA cache_size=-65536")  # 64 MB cache
    cur = sq.cursor()

    # ========================================================================
    # 1. SINAPI — composicoes (filtradas CE + SEM)
    # ========================================================================
    print("\n[1/6] SINAPI — composicoes (CE + SEM)...")
    t0 = time.time()

    conn = get_mysql(DB_SINAPI)
    rows = fetch_all(
        conn,
        """SELECT codigo, descricao, unidade,
                  ROUND(custo, 2) AS custo,
                  grupo
           FROM composicoes
           WHERE uf = 'CE' AND tipo_desoneracao = 'SEM'
           ORDER BY descricao""",
    )
    n_comp = len(rows)
    conn.close()

    create_sqlite_table(
        cur,
        "sinapi_composicoes",
        [
            "codigo INTEGER PRIMARY KEY",
            "descricao TEXT",
            "unidade TEXT",
            "custo REAL",
            "grupo TEXT",
        ],
        indexes=[
            ("idx_sinapi_comp_codigo", "codigo"),
            ("idx_sinapi_comp_grupo", "grupo"),
        ],
    )

    for i, r in enumerate(rows):
        cur.execute(
            "INSERT INTO sinapi_composicoes VALUES (?,?,?,?,?)",
            (r["codigo"], r["descricao"], r["unidade"], to_float(r["custo"]), r["grupo"]),
        )
        if i % 500 == 0 or i == n_comp - 1:
            progress("composicoes", i + 1, n_comp)
    print(f"\n  OK: {n_comp} composições em {time.time()-t0:.1f}s")

    # ========================================================================
    # 2. SINAPI — composicao_itens (apenas das composições filtradas)
    # ========================================================================
    print("\n[2/6] SINAPI — composicao_itens...")
    t0 = time.time()

    conn = get_mysql(DB_SINAPI)

    # Pega os códigos das composições filtradas
    codigos = [r["codigo"] for r in rows]
    # Busca em lotes de 5000 para evitar query muito grande
    all_itens = []
    batch_size = 5000
    for batch_start in range(0, len(codigos), batch_size):
        batch = codigos[batch_start : batch_start + batch_size]
        placeholders = ",".join(["%s"] * len(batch))
        itens = fetch_all(
            conn,
            f"""SELECT codigo_composicao, tipo_item, codigo_item,
                       descricao, unidade, coeficiente, situacao
                FROM composicao_itens
                WHERE codigo_composicao IN ({placeholders})
                ORDER BY codigo_composicao, tipo_item, descricao""",
            tuple(batch),
        )
        all_itens.extend(itens)
        progress("buscando itens", batch_start + len(batch), len(codigos))
    conn.close()

    n_itens = len(all_itens)

    create_sqlite_table(
        cur,
        "sinapi_composicao_itens",
        [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "codigo_composicao INTEGER",
            "tipo_item TEXT",
            "codigo_item TEXT",
            "descricao TEXT",
            "unidade TEXT",
            "coeficiente REAL",
            "situacao TEXT",
        ],
        indexes=[
            ("idx_sinapi_itens_comp", "codigo_composicao"),
            ("idx_sinapi_itens_coditem", "codigo_item"),
        ],
    )

    for i, r in enumerate(all_itens):
        cur.execute(
            "INSERT INTO sinapi_composicao_itens VALUES (NULL,?,?,?,?,?,?,?)",
            (
                r["codigo_composicao"],
                r["tipo_item"],
                r["codigo_item"],
                r["descricao"],
                r["unidade"],
                to_float(r["coeficiente"]),
                r["situacao"],
            ),
        )
        if i % 5000 == 0 or i == n_itens - 1:
            progress("gravando itens", i + 1, n_itens)
    print(f"\n  OK: {n_itens} itens de composição em {time.time()-t0:.1f}s")

    # ========================================================================
    # 3. SINAPI — insumos (apenas os referenciados nos itens)
    # ========================================================================
    print("\n[3/6] SINAPI — insumos (apenas referenciados)...")
    t0 = time.time()

    # Coleta códigos de insumos distintos
    codigos_insumos = list(
        {r["codigo_item"] for r in all_itens if r["tipo_item"] == "INSUMO"}
    )
    print(f"  {len(codigos_insumos)} códigos de insumos únicos para buscar")

    conn = get_mysql(DB_SINAPI)
    all_insumos = []
    batch_size = 5000
    for batch_start in range(0, len(codigos_insumos), batch_size):
        batch = codigos_insumos[batch_start : batch_start + batch_size]
        placeholders = ",".join(["%s"] * len(batch))
        insumos = fetch_all(
            conn,
            f"""SELECT codigo, descricao, unidade, valor
                FROM insumos
                WHERE codigo IN ({placeholders})
                  AND uf = 'CE'
                  AND tipo_desoneracao = 'SEM'""",
            tuple(batch),
        )
        all_insumos.extend(insumos)
        progress("buscando insumos", batch_start + len(batch), len(codigos_insumos))
    conn.close()

    n_ins = len(all_insumos)

    create_sqlite_table(
        cur,
        "sinapi_insumos",
        [
            "codigo TEXT PRIMARY KEY",
            "descricao TEXT",
            "unidade TEXT",
            "valor REAL",
        ],
        indexes=[("idx_sinapi_insumos_codigo", "codigo")],
    )

    for i, r in enumerate(all_insumos):
        cur.execute(
            "INSERT INTO sinapi_insumos VALUES (?,?,?,?)",
            (r["codigo"], r["descricao"], r["unidade"], to_float(r["valor"])),
        )
        if i % 5000 == 0 or i == n_ins - 1:
            progress("gravando insumos", i + 1, n_ins)
    print(f"\n  OK: {n_ins} insumos (com preço CE) em {time.time()-t0:.1f}s")

    # ========================================================================
    # 4. SEINFRA — composicoes
    # ========================================================================
    print("\n[4/6] SEINFRA — composicoes...")
    t0 = time.time()

    conn = get_mysql(DB_SEINFRA)
    rows = fetch_all(
        conn,
        """SELECT codigo, descricao, unidade,
                  ROUND(preco_unitario, 2) AS preco_unitario
           FROM composicoes
           ORDER BY descricao""",
    )
    n_comp_se = len(rows)
    conn.close()

    create_sqlite_table(
        cur,
        "seinfra_composicoes",
        [
            "codigo TEXT PRIMARY KEY",
            "descricao TEXT",
            "unidade TEXT",
            "preco_unitario REAL",
        ],
        indexes=[("idx_seinfra_comp_codigo", "codigo")],
    )

    for i, r in enumerate(rows):
        cur.execute(
            "INSERT INTO seinfra_composicoes VALUES (?,?,?,?)",
            (r["codigo"], r["descricao"], r["unidade"], to_float(r["preco_unitario"])),
        )
        if i % 500 == 0 or i == n_comp_se - 1:
            progress("composicoes", i + 1, n_comp_se)
    print(f"\n  OK: {n_comp_se} composições em {time.time()-t0:.1f}s")

    # ========================================================================
    # 5. SEINFRA — composicao_itens
    # ========================================================================
    print("\n[5/6] SEINFRA — composicao_itens...")
    t0 = time.time()

    conn = get_mysql(DB_SEINFRA)
    itens = fetch_all(
        conn,
        """SELECT codigo_composicao, codigo_item,
                  descricao_item, unidade_item,
                  categoria, coeficiente,
                  ROUND(preco_unitario, 4) AS preco_unitario,
                  ROUND(total, 4) AS total_item
           FROM composicao_itens
           ORDER BY codigo_composicao, categoria, descricao_item""",
    )
    n_itens_se = len(itens)
    conn.close()

    create_sqlite_table(
        cur,
        "seinfra_composicao_itens",
        [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "codigo_composicao TEXT",
            "codigo_item TEXT",
            "descricao_item TEXT",
            "unidade_item TEXT",
            "categoria TEXT",
            "coeficiente REAL",
            "preco_unitario REAL",
            "total_item REAL",
        ],
        indexes=[
            ("idx_seinfra_itens_comp", "codigo_composicao"),
        ],
    )

    for i, r in enumerate(itens):
        cur.execute(
            "INSERT INTO seinfra_composicao_itens VALUES (NULL,?,?,?,?,?,?,?,?)",
            (
                r["codigo_composicao"],
                r["codigo_item"],
                r["descricao_item"],
                r["unidade_item"],
                r["categoria"],
                to_float(r["coeficiente"]),
                to_float(r["preco_unitario"]),
                to_float(r["total_item"]),
            ),
        )
        if i % 5000 == 0 or i == n_itens_se - 1:
            progress("itens", i + 1, n_itens_se)
    print(f"\n  OK: {n_itens_se} itens de composição em {time.time()-t0:.1f}s")

    # ========================================================================
    # 6. SEINFRA — planos_servicos (árvore hierárquica)
    # ========================================================================
    print("\n[6/6] SEINFRA — planos_servicos (hierarquia)...")
    t0 = time.time()

    conn = get_mysql(DB_SEINFRA)
    ps_rows = fetch_all(
        conn,
        """SELECT item, codigo, descricao, unidade,
                  ROUND(preco_unitario, 2) AS preco_unitario,
                  nivel
           FROM planos_servicos
           ORDER BY item""",
    )
    n_ps = len(ps_rows)
    conn.close()

    create_sqlite_table(
        cur,
        "seinfra_planos_servicos",
        [
            "item TEXT",
            "codigo TEXT",
            "descricao TEXT",
            "unidade TEXT",
            "preco_unitario REAL",
            "nivel INTEGER",
        ],
        indexes=[
            ("idx_seinfra_ps_nivel", "nivel"),
            ("idx_seinfra_ps_item", "item"),
            ("idx_seinfra_ps_codigo", "codigo"),
        ],
    )

    for i, r in enumerate(ps_rows):
        cur.execute(
            "INSERT INTO seinfra_planos_servicos VALUES (?,?,?,?,?,?)",
            (
                r["item"],
                r["codigo"],
                r["descricao"],
                r["unidade"],
                to_float(r["preco_unitario"]),
                r["nivel"],
            ),
        )
        if i % 500 == 0 or i == n_ps - 1:
            progress("planos", i + 1, n_ps)
    print(f"\n  OK: {n_ps} nós da hierarquia em {time.time()-t0:.1f}s")

    # ========================================================================
    # Finalização
    # ========================================================================
    print("\n" + "=" * 60)
    sq.commit()
    sq.close()

    # Verificação final
    verify = sqlite3.connect(OUTPUT_DB)
    v = verify.cursor()

    resumo = {}
    for tbl in [
        "sinapi_composicoes",
        "sinapi_composicao_itens",
        "sinapi_insumos",
        "seinfra_composicoes",
        "seinfra_composicao_itens",
        "seinfra_planos_servicos",
    ]:
        v.execute(f"SELECT COUNT(*) FROM {tbl}")
        resumo[tbl] = v.fetchone()[0]

    verify.close()

    print("  RESUMO DA EXPORTAÇÃO")
    print("-" * 60)
    print(f"  {'Tabela':<35} {'Linhas':>8}")
    print("-" * 60)
    for tbl, cnt in resumo.items():
        print(f"  {tbl:<35} {cnt:>8,}")
    print("-" * 60)

    tamanho_mb = os.path.getsize(OUTPUT_DB) / (1024 * 1024)
    print(f"\n  Arquivo: {OUTPUT_DB}")
    print(f"  Tamanho: {tamanho_mb:.1f} MB")
    print(f"\n  ✅ Exportação concluída com sucesso!")
    print("=" * 60)


if __name__ == "__main__":
    main()
