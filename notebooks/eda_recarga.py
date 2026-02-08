# -*- coding: utf-8 -*-
"""
Versão 2: usando polars em vez de duckDB
31/01/26
"""

# ============================================================
# EDA – Base de Recarga
# ============================================================

import polars as pl
import time
import matplotlib.pyplot as plt
from datetime import timedelta
import os

# ============================================================
# [1] Leitura lazy dos Parquet
# ============================================================
t0 = time.time()
eventos = (
    pl.scan_parquet(
        "C:/Users/cezar/Downloads/hackathon/bases_recarga/"
        "BI_FP_ASS_RECARGA_CMV_NOVA/part-*.parquet"
    )
)
print(f"[OK] Scan parquet configurado em {time.time() - t0:.2f}s")

# ============================================================
# [2] Tipagem e normalização mínima (EDA)
# ============================================================
t0 = time.time()
eventos_typed = (
    eventos
    .with_columns([

        # ------------------------
        # Data: DDMMMYYYY (ex: 01JAN2024)
        # ------------------------
        pl.col("DAT_INSERCAO_CREDITO")
          .str.slice(0, 9)
          .str.strptime(pl.Date, "%d%b%Y", strict=False)
          .alias("DAT_INSERCAO_CREDITO"),

        # ------------------------
        # Hora: HHMMSS (com padding)
        # ------------------------
        (
            pl.col("HOR_INSERCAO_CREDITO")
              .cast(pl.Utf8)
              .str.zfill(6)
              .str.slice(0, 2) + ":" +
            pl.col("HOR_INSERCAO_CREDITO")
              .cast(pl.Utf8)
              .str.zfill(6)
              .str.slice(2, 2) + ":" +
            pl.col("HOR_INSERCAO_CREDITO")
              .cast(pl.Utf8)
              .str.zfill(6)
              .str.slice(4, 2)
        )
        .str.strptime(pl.Time, "%H:%M:%S", strict=False)
        .alias("HOR_INSERCAO_CREDITO"),

        # ------------------------
        # Métricas numéricas
        # ------------------------
        pl.col("VAL_CREDITO_INSERIDO").cast(pl.Float64, strict=False),
        pl.col("VAL_BONUS").cast(pl.Float64, strict=False),
        pl.col("VAL_REAL").cast(pl.Float64, strict=False),
        pl.col("VALOR_SOS").cast(pl.Float64, strict=False),

    ])
)
print(f"[OK] View tipada (lazy) criada em {time.time() - t0:.2f}s")

#contagem de CPFs distintos
cpf_stats = (
    eventos_typed
    .select([
        pl.count().alias("total_linhas"),
        pl.col("NUM_CPF").null_count().alias("cpf_nulos"),
        pl.col("NUM_CPF").n_unique().alias("cpf_distintos"),
    ])
    .collect()
)
print(cpf_stats)
#3077601

#contabulizar CPFs com >=2 NUM_CLIENTE e >=2 NUM_NTC
cpf_cliente_dist = (
    eventos_typed
    .select(["NUM_CPF", "DW_NUM_CLIENTE"])
    .unique()
    .group_by("NUM_CPF")
    .agg(pl.count().alias("qtd_clientes_distintos"))
    .select(pl.col("qtd_clientes_distintos").value_counts())
    .sort("qtd_clientes_distintos")
    .collect()
)
print(cpf_cliente_dist)

cpf_ntc_dist = (
    eventos_typed
    .select(["NUM_CPF", "DW_NUM_NTC"])
    .unique()
    .group_by("NUM_CPF")
    .agg(pl.count().alias("qtd_ntc_distintos"))
    .select(pl.col("qtd_ntc_distintos").value_counts())
    .sort("qtd_ntc_distintos")
    .collect()
)
print(cpf_ntc_dist)

# gráficos
# Extrai colunas da struct
df_cliente = cpf_cliente_dist.with_columns([
    pl.col("qtd_clientes_distintos").struct.field("qtd_clientes_distintos").alias("n_clientes"),
    pl.col("qtd_clientes_distintos").struct.field("count").alias("n_cpfs")
]).select(["n_clientes", "n_cpfs"]).to_pandas()

plt.figure()
plt.bar(df_cliente["n_clientes"], df_cliente["n_cpfs"])
plt.yscale("log")
plt.xlabel("Número de clientes distintos por CPF")
plt.ylabel("Quantidade de CPFs (escala log)")
plt.title("Distribuição de CPFs por número de clientes distintos")
plt.show()

df_ntc = cpf_ntc_dist.with_columns([
    pl.col("qtd_ntc_distintos").struct.field("qtd_ntc_distintos").alias("n_ntc"),
    pl.col("qtd_ntc_distintos").struct.field("count").alias("n_cpfs")
]).select(["n_ntc", "n_cpfs"]).to_pandas()

plt.figure()
plt.bar(df_ntc["n_ntc"], df_ntc["n_cpfs"])
plt.yscale("log")
plt.xlabel("Número de NTCs distintos por CPF")
plt.ylabel("Quantidade de CPFs (escala log)")
plt.title("Distribuição de CPFs por número de NTCs distintos")
plt.show()

#re-checando variáveis monetárias
def summary_coluna(lf: pl.LazyFrame, col: str) -> pl.DataFrame:
    return (
        lf
        .select([
            pl.col(col).count().alias("count"),
            pl.col(col).null_count().alias("nulls"),
            pl.col(col).min().alias("min"),
            pl.col(col).quantile(0.01).alias("p01"),
            pl.col(col).quantile(0.05).alias("p05"),
            pl.col(col).median().alias("median"),
            pl.col(col).mean().alias("mean"),
            pl.col(col).quantile(0.95).alias("p95"),
            pl.col(col).quantile(0.99).alias("p99"),
            pl.col(col).max().alias("max"),
        ])
        .with_columns(pl.lit(col).alias("variavel"))
        .collect()
        .select([
            "variavel",
            "count",
            "nulls",
            "min",
            "p01",
            "p05",
            "median",
            "mean",
            "p95",
            "p99",
            "max",
        ])
    )
summary_monetario = pl.concat([
    summary_coluna(eventos_typed, "VAL_CREDITO_INSERIDO"),
    summary_coluna(eventos_typed, "VAL_BONUS"),
    summary_coluna(eventos_typed, "VAL_REAL"),
    summary_coluna(eventos_typed, "VALOR_SOS"),
])
print(summary_monetario)

##################################################
#inspecionando BUREAU para filtro e adquirir FPD

# ============================================================
# INSPEÇÃO INICIAL – BASE BUREAU (PARQUET)
# ============================================================

t0 = time.time()
bureau = pl.scan_parquet(
    r"C:\Users\cezar\Downloads\hackathon\base_score_bureau_movel\part-00000-b6bf6bdd-9a2d-4bc5-a97c-fa8553906bc9-c000.snappy.parquet"
)
print(f"[OK] Bureau carregado em modo lazy ({time.time() - t0:.2f}s)")

# ------------------------------------------------------------
# [1] Estrutura da base
# ------------------------------------------------------------
print("\n[SCHEMA]")
print(bureau.schema)

# ------------------------------------------------------------
# [2] Estatísticas básicas (volume e CPF)
# ------------------------------------------------------------
t0 = time.time()
bureau_stats = (
    bureau
    .select([
        pl.count().alias("total_linhas"),
        pl.col("NUM_CPF").null_count().alias("cpf_nulos"),
        pl.col("NUM_CPF").n_unique().alias("cpf_distintos"),
    ])
    .collect()
)
print("\n[STATS GERAIS]")
print(bureau_stats)
print(f"[OK] Estatísticas calculadas em {time.time() - t0:.2f}s")

# ------------------------------------------------------------
# [3] Checagem rápida de duplicidade de CPF
# ------------------------------------------------------------
t0 = time.time()
cpf_multiplos = (
    bureau
    .group_by("NUM_CPF")
    .agg(pl.len().alias("qtd_registros"))
    .select(pl.col("qtd_registros").value_counts())
    .sort("qtd_registros")
    .collect()
)
print("\n[DISTRIBUIÇÃO – REGISTROS POR CPF]")
print(cpf_multiplos)
print(f"[OK] Distribuição calculada em {time.time() - t0:.2f}s")

# ------------------------------------------------------------
# [4] Prévia controlada (apenas para inspeção visual)
# ------------------------------------------------------------
print("\n[HEAD – AMOSTRA]")
print(bureau.select(pl.all()).head(5).collect())

#CPFs em cada safra
# ============================================================
# DISTRIBUIÇÃO DE CPFs POR SAFRA – BUREAU
# ============================================================
t0 = time.time()
cpf_por_safra = (
    bureau
    .select(["SAFRA", "NUM_CPF"])
    .unique()
    .group_by("SAFRA")
    .agg(pl.len().alias("cpfs_distintos"))
    .sort("SAFRA")
    .collect()
)
print(cpf_por_safra)
print(f"[OK] Distribuição por SAFRA calculada em {time.time() - t0:.2f}s")


#início do JOIN, trazendo Safra mais recente e FPD
# ============================================================
# [A] Bureau – SAFRA mais recente por CPF
# ============================================================
t0 = time.time()
bureau_latest = (
    bureau
    .select(["NUM_CPF", "SAFRA", "FPD"])
    .with_columns(pl.col("SAFRA").cast(pl.Int32))
    .sort(["NUM_CPF", "SAFRA"])
    .group_by("NUM_CPF")
    .agg([
        pl.last("SAFRA").alias("SAFRA"),
        pl.last("FPD").alias("FPD_SCORE"),  # ← padronização aqui
    ])
)
print(f"[OK] Bureau reduzido para SAFRA mais recente por CPF ({time.time() - t0:.2f}s)")

# ============================================================
# [B] INNER JOIN – Recarga × Bureau (CPF)
# ============================================================
t0 = time.time()
eventos_com_bureau = (
    eventos_typed
    .join(
        bureau_latest,
        on="NUM_CPF",
        how="inner"
    )
)
print(f"[OK] INNER JOIN realizado ({time.time() - t0:.2f}s)")

# ============================================================
# [C] Validações pós-join
# ============================================================
t0 = time.time()
checks = (
    eventos_com_bureau
    .select([
        pl.count().alias("total_linhas"),
        pl.col("NUM_CPF").n_unique().alias("cpf_distintos"),
        pl.col("FPD_SCORE").null_count().alias("fpd_nulos"),
        pl.col("SAFRA").n_unique().alias("safras_presentes"),
    ])
    .collect()
)
print("\n[CHECKS PÓS-JOIN]")
print(checks)
print(f"[OK] Checks calculados em {time.time() - t0:.2f}s")

####################
#seguindo metodologia do Dayan a partir daqui
#Criar chave temporal mensal
eventos_mensal = (
    eventos_com_bureau
    .with_columns(
        pl.col("DAT_INSERCAO_CREDITO")
          .dt.strftime("%Y%m")
          .alias("ANO_MES")
    )
)
#1. Agregar CPF × mês
perfil_cpf_mes = (
    eventos_mensal
    .group_by(["NUM_CPF", "ANO_MES"])
    .agg([
        pl.len().alias("qtd_recargas_mes"),
        pl.col("VAL_CREDITO_INSERIDO").sum().alias("valor_total_mes"),
        pl.col("VAL_CREDITO_INSERIDO").mean().alias("ticket_medio_mes"),
        pl.col("VAL_CREDITO_INSERIDO").max().alias("valor_max_mes"),
        pl.col("DAT_INSERCAO_CREDITO").n_unique().alias("dias_ativos_mes"),
        pl.first("FPD_SCORE").alias("FPD_SCORE"),
        pl.first("SAFRA").alias("SAFRA"),
    ])
)
#cria a chave mensal ANO_MES na base de recarga já joinada
t0 = time.time()
eventos_mensal = (
    eventos_com_bureau
    .with_columns(
        pl.col("DAT_INSERCAO_CREDITO")
          .dt.strftime("%Y%m")
          .alias("ANO_MES")
    )
)
# sanity check rápido (não pesado)
check_ano_mes = (
    eventos_mensal
    .select([
        pl.col("ANO_MES").null_count().alias("ano_mes_nulos"),
        pl.col("ANO_MES").n_unique().alias("ano_mes_distintos"),
        pl.col("ANO_MES").min().alias("ano_mes_min"),
        pl.col("ANO_MES").max().alias("ano_mes_max"),
    ])
    .collect()
)
print(check_ano_mes)
print(f"[OK] Passo 1 concluído em {time.time() - t0:.2f}s")

#2. Agregar CPF × ANO_MES (perfil mensal)
t0 = time.time()
perfil_cpf_mes = (
    eventos_mensal
    .group_by(["NUM_CPF", "ANO_MES"])
    .agg([
        pl.len().alias("qtd_recargas_mes"),
        pl.col("VAL_CREDITO_INSERIDO").sum().alias("valor_total_mes"),
        pl.col("VAL_CREDITO_INSERIDO").mean().alias("ticket_medio_mes"),
        pl.col("VAL_CREDITO_INSERIDO").max().alias("valor_max_mes"),
        pl.col("DAT_INSERCAO_CREDITO").n_unique().alias("dias_ativos_mes"),
        pl.first("FPD_SCORE").alias("FPD_SCORE"),
        pl.first("SAFRA").alias("SAFRA"),
    ])
)
print(f"[OK] Passo 2 concluído em {time.time() - t0:.2f}s")
t0 = time.time()
#sanity checks
checks_agreg = (
    perfil_cpf_mes
    .select([
        pl.count().alias("linhas_cpf_mes"),
        pl.col("NUM_CPF").n_unique().alias("cpf_distintos"),
        pl.col("ANO_MES").n_unique().alias("meses_distintos"),
        pl.col("FPD_SCORE").null_count().alias("fpd_nulos"),
    ])
    .collect()
)
print("\n[CHECKS – CPF × ANO_MES]")
print(checks_agreg)
print(f"[OK] Checks calculados em {time.time() - t0:.2f}s")

#3. Perfil estável por CPF (resumo longitudinal)
#Variáveis a criar por CPF:
#Volume / frequência
#meses_ativos
#media_recargas_mes
#mediana_recargas_mes
#Valor
#media_valor_mes
#mediana_valor_mes
#media_ticket
#max_valor_mes
#Regularidade
#desvio_recargas_mes
#desvio_valor_mes
t0 = time.time()
perfil_cpf = (
    perfil_cpf_mes
    .group_by("NUM_CPF")
    .agg([
        # Atividade temporal
        pl.col("ANO_MES").n_unique().alias("meses_ativos"),

        # Frequência
        pl.col("qtd_recargas_mes").mean().alias("media_recargas_mes"),
        pl.col("qtd_recargas_mes").median().alias("mediana_recargas_mes"),
        pl.col("qtd_recargas_mes").std().alias("desvio_recargas_mes"),

        # Valor total mensal
        pl.col("valor_total_mes").mean().alias("media_valor_mes"),
        pl.col("valor_total_mes").median().alias("mediana_valor_mes"),
        pl.col("valor_total_mes").std().alias("desvio_valor_mes"),
        pl.col("valor_total_mes").max().alias("max_valor_mes"),

        # Ticket
        pl.col("ticket_medio_mes").mean().alias("media_ticket"),

        # Âncoras
        pl.first("FPD_SCORE").alias("FPD_SCORE"),
        pl.first("SAFRA").alias("SAFRA"),
    ])
)
print(f"[OK] Passo 3 concluído em {time.time() - t0:.2f}s")
#checks
t0 = time.time()
checks_perfil = (
    perfil_cpf
    .select([
        pl.count().alias("cpf_total"),
        pl.col("meses_ativos").min().alias("min_meses"),
        pl.col("meses_ativos").max().alias("max_meses"),
        pl.col("FPD_SCORE").null_count().alias("fpd_nulos"),
    ])
    .collect()
)
print("\n[CHECKS – Perfil por CPF]")
print(checks_perfil)
print(f"[OK] Checks calculados em {time.time() - t0:.2f}s")

##############################
#gambiarra
# Distribuição de CLIENTES por CPF
cpf_qtd_clientes = (
    eventos_com_bureau
    .select(["NUM_CPF", "DW_NUM_CLIENTE"])
    .unique()
    .group_by("NUM_CPF")
    .agg(pl.len().alias("qtd_clientes"))
    .group_by("qtd_clientes")
    .agg(pl.len().alias("qtd_cpfs"))
    .sort("qtd_clientes")
    .collect()
)

##################################
# Distribuição de NTCs por CPF
##################################
cpf_qtd_ntc = (
    eventos_com_bureau
    .select(["NUM_CPF", "DW_NUM_NTC"])
    .unique()
    .group_by("NUM_CPF")
    .agg(pl.len().alias("qtd_ntcs"))
    .group_by("qtd_ntcs")
    .agg(pl.len().alias("qtd_cpfs"))
    .sort("qtd_ntcs")
    .collect()
)

# GRÁFICO 1 — CLIENTES
cpf_qtd_clientes_plot = cpf_qtd_clientes.filter(
    pl.col("qtd_clientes") <= 12
)

plt.figure(figsize=(10, 5))
plt.bar(
    cpf_qtd_clientes_plot["qtd_clientes"],
    cpf_qtd_clientes_plot["qtd_cpfs"]
)
plt.xlim(0, 12)
plt.xlabel("Número de clientes distintos por CPF")
plt.ylabel("Quantidade de CPFs")
plt.title("Distribuição de CPFs por número de clientes distintos (pós-Bureau)")
plt.tight_layout()
plt.show()


# GRÁFICO 2 — NTCs
cpf_qtd_ntc_plot = cpf_qtd_ntc.filter(
    pl.col("qtd_ntcs") <= 7
)

plt.figure(figsize=(10, 5))
plt.bar(
    cpf_qtd_ntc_plot["qtd_ntcs"],
    cpf_qtd_ntc_plot["qtd_cpfs"]
)
plt.xlim(0, 7)
plt.xlabel("Número de NTCs distintos por CPF")
plt.ylabel("Quantidade de CPFs")
plt.title("Distribuição de CPFs por número de NTCs distintos (pós-Bureau)")
plt.tight_layout()
plt.show()


#######################################
#início de inspeção e uso das dimensões

################################
# PASSO 4.1 — BI_DIM_INSTITUICAO
################################

t0 = time.time()
# 0) Tipagem da chave para join (base eventos)
eventos_com_bureau = (
    eventos_com_bureau
    .with_columns(
        pl.col("DW_INSTITUICAO")
        .cast(pl.Int64, strict=False)   # inválidos → null
        .alias("DW_INSTITUICAO")
    )
)
# 1) Leitura da dimensão
dim_instituicao = (
    pl.read_csv(
        r"C:\Users\cezar\Downloads\hackathon\bases_recarga\BI_DIM_INSTITUICAO.csv"
    )
    .select(["DW_INSTITUICAO", "COD_TIPO_INSTITUICAO"])
    .with_columns(
        pl.col("COD_TIPO_INSTITUICAO")
        .cast(pl.Int64, strict=False)
    )
    .lazy()
)
# 2) Join eventos × dimensão
eventos_inst = (
    eventos_com_bureau
    .join(
        dim_instituicao,
        on="DW_INSTITUICAO",
        how="left"
    )
)
# 3) Agregação por CPF
perfil_inst_cpf = (
    eventos_inst
    .group_by("NUM_CPF")
    .agg([
        # Tipo de instituição dominante
        pl.col("COD_TIPO_INSTITUICAO")
          .drop_nulls()
          .mode()
          .first()
          .fill_null("SEM_INFORMACAO")
          .alias("tipo_instituicao_dominante"),

        # Diversidade institucional (ignorando null)
        pl.col("COD_TIPO_INSTITUICAO")
          .drop_nulls()
          .n_unique()
          .alias("qtd_tipos_instituicao"),
    ])
)
print(f"[OK] BI_DIM_INSTITUICAO processada em {time.time() - t0:.2f}s")
# 4) CHECKS
checks_inst = (
    perfil_inst_cpf
    .select([
        pl.len().alias("cpfs_total"),
        (pl.col("tipo_instituicao_dominante") == "SEM_INFORMACAO")
            .sum()
            .alias("sem_informacao"),
        pl.col("qtd_tipos_instituicao").max().alias("max_diversidade"),
    ])
    .collect()
)
print("\n[CHECKS — BI_DIM_INSTITUICAO]")
print(checks_inst)
# 5) INSPEÇÕES — Frequências
# 5.1 Frequência do tipo de instituição dominante
freq_tipo_inst = (
    perfil_inst_cpf
    .group_by("tipo_instituicao_dominante", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs") / pl.col("qtd_cpfs").sum()).alias("perc_cpfs")
    )
    .sort("qtd_cpfs", descending=True)
    .collect()
)
print("\n[FREQUÊNCIA — tipo_instituicao_dominante]")
print(freq_tipo_inst)
# 5.2 Frequência da diversidade institucional
freq_diversidade_inst = (
    perfil_inst_cpf
    .group_by("qtd_tipos_instituicao", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs") / pl.col("qtd_cpfs").sum()).alias("perc_cpfs")
    )
    .sort("qtd_tipos_instituicao")
    .collect()
)
print("\n[FREQUÊNCIA — qtd_tipos_instituicao]")
print(freq_diversidade_inst)
# 6) CROSS — dominante × diversidade
cross_inst = (
    perfil_inst_cpf
    .group_by(
        ["tipo_instituicao_dominante", "qtd_tipos_instituicao"],
        maintain_order=True
    )
    .agg(pl.len().alias("qtd_cpfs"))
    .sort(["tipo_instituicao_dominante", "qtd_tipos_instituicao"])
    .collect()
)
print("\n[CROSS — tipo_instituicao_dominante × qtd_tipos_instituicao]")
print(cross_inst)

#################################################################
# AS DEMAIS DIMENSÕES SÃO INÚTREIS EM VARIAÇÃO NO FILTRO BUREAU #
# PODE IGNORAR OS PASSOS 4.2 A 4.11                             #

###################################
# PASSO 4.2 — BI_DIM_TIPO_INSERCAO
###################################
# tipagem para join
eventos_com_bureau = (
    eventos_com_bureau
    .with_columns(
        pl.col("DW_TIPO_INSERCAO")
        .cast(pl.Int64, strict=False)
        .alias("DW_TIPO_INSERCAO")
    )
)
t0 = time.time()
# 1) Leitura e transformação da dimensão
dim_tipo_insercao = (
    pl.read_csv(
        r"C:\Users\cezar\Downloads\hackathon\bases_recarga\BI_DIM_TIPO_INSERCAO.csv"
    )
    .select(["DW_TIPO_INSERCAO", "DSC_TIPO_INSERCAO"])
    .with_columns(
        pl.when(pl.col("DW_TIPO_INSERCAO") < 0)
          .then(pl.lit("SEM_INFORMACAO"))
        .when(pl.col("DW_TIPO_INSERCAO").is_between(11, 19))
          .then(pl.lit("BONUS"))
        .otherwise(pl.col("DSC_TIPO_INSERCAO"))
        .alias("TIPO_INSERCAO_NORMALIZADO")
    )
    .select(["DW_TIPO_INSERCAO", "TIPO_INSERCAO_NORMALIZADO"])
    .lazy()
)
# 2) Join com eventos
eventos_tipo_ins = (
    eventos_com_bureau
    .join(
        dim_tipo_insercao,
        on="DW_TIPO_INSERCAO",
        how="left"
    )
)
# 3) Agregação por CPF
perfil_tipo_ins_cpf = (
    eventos_tipo_ins
    .group_by("NUM_CPF")
    .agg([
        pl.col("TIPO_INSERCAO_NORMALIZADO")
          .drop_nulls()
          .mode()
          .first()
          .alias("tipo_insercao_dominante"),
        pl.col("TIPO_INSERCAO_NORMALIZADO")
          .n_unique()
          .alias("qtd_tipos_insercao"),
    ])
)
print(f"[OK] BI_DIM_TIPO_INSERCAO processada em {time.time() - t0:.2f}s")
# 4) CHECKS
checks_tipo_ins = (
    perfil_tipo_ins_cpf
    .select([
        pl.count().alias("cpfs_total"),
        pl.col("tipo_insercao_dominante")
          .filter(pl.col("tipo_insercao_dominante") == "SEM_INFORMACAO")
          .count()
          .alias("sem_informacao"),
        pl.col("qtd_tipos_insercao").max().alias("max_diversidade"),
    ])
    .collect()
)
print("\n[CHECKS — BI_DIM_TIPO_INSERCAO]")
print(checks_tipo_ins)
# 5) FREQUÊNCIA — dominante
freq_tipo_ins = (
    perfil_tipo_ins_cpf
    .group_by("tipo_insercao_dominante", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs") / pl.col("qtd_cpfs").sum()).alias("perc_cpfs")
    )
    .sort("qtd_cpfs", descending=True)
    .collect()
)
print("\n[FREQUÊNCIA — tipo_insercao_dominante]")
print(freq_tipo_ins)
# 6) FREQUÊNCIA — diversidade
freq_div_tipo_ins = (
    perfil_tipo_ins_cpf
    .group_by("qtd_tipos_insercao", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs") / pl.col("qtd_cpfs").sum()).alias("perc_cpfs")
    )
    .sort("qtd_tipos_insercao")
    .collect()
)
print("\n[FREQUÊNCIA — qtd_tipos_insercao]")
print(freq_div_tipo_ins)
# 7) CROSS — dominante × diversidade
cross_tipo_ins = (
    perfil_tipo_ins_cpf
    .group_by(["tipo_insercao_dominante", "qtd_tipos_insercao"], maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .sort(["tipo_insercao_dominante", "qtd_tipos_insercao"])
    .collect()
)
print("\n[CROSS — tipo_insercao_dominante × qtd_tipos_insercao]")
print(cross_tipo_ins)
#dimensão sem variabilidade útil

###################################
# PASSO 4.3 — BI_DIM_TIPO_RECARGA
###################################
# tipagem para join
eventos_com_bureau = (
    eventos_com_bureau
    .with_columns(
        pl.col("DW_TIPO_RECARGA")
        .cast(pl.Int64, strict=False)
        .alias("DW_TIPO_RECARGA")
    )
)
t0 = time.time()
# 1) Leitura e transformação da dimensão
dim_tipo_recarga = (
    pl.read_csv(
        r"C:\Users\cezar\Downloads\hackathon\bases_recarga\BI_DIM_TIPO_RECARGA.csv"
    )
    .select(["DW_TIPO_RECARGA"])
    .with_columns(
        pl.when(pl.col("DW_TIPO_RECARGA") < 0)
          .then(pl.lit("SEM_INFORMACAO"))
        .when(pl.col("DW_TIPO_RECARGA") == 1)
          .then(pl.lit("FRANQUIA"))
        .when(pl.col("DW_TIPO_RECARGA") == 2)
          .then(pl.lit("ADICIONAL"))
        .otherwise(pl.lit("SEM_INFORMACAO"))
        .alias("TIPO_RECARGA_NORMALIZADO")
    )
    .select(["DW_TIPO_RECARGA", "TIPO_RECARGA_NORMALIZADO"])
    .lazy()
)
# 2) Join com eventos
eventos_tipo_rec = (
    eventos_com_bureau
    .join(
        dim_tipo_recarga,
        on="DW_TIPO_RECARGA",
        how="left"
    )
)
# 3) Agregação por CPF
perfil_tipo_rec_cpf = (
    eventos_tipo_rec
    .group_by("NUM_CPF")
    .agg([
        pl.col("TIPO_RECARGA_NORMALIZADO")
          .drop_nulls()
          .mode()
          .first()
          .alias("tipo_recarga_dominante"),
        pl.col("TIPO_RECARGA_NORMALIZADO")
          .n_unique()
          .alias("qtd_tipos_recarga"),
    ])
)
print(f"[OK] BI_DIM_TIPO_RECARGA processada em {time.time() - t0:.2f}s")
# 4) CHECKS
checks_tipo_rec = (
    perfil_tipo_rec_cpf
    .select([
        pl.count().alias("cpfs_total"),
        pl.col("tipo_recarga_dominante")
          .filter(pl.col("tipo_recarga_dominante") == "SEM_INFORMACAO")
          .count()
          .alias("sem_informacao"),
        pl.col("qtd_tipos_recarga").max().alias("max_diversidade"),
    ])
    .collect()
)
print("\n[CHECKS — BI_DIM_TIPO_RECARGA]")
print(checks_tipo_rec)
# 5) FREQUÊNCIA — dominante
freq_tipo_rec = (
    perfil_tipo_rec_cpf
    .group_by("tipo_recarga_dominante", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs") / pl.col("qtd_cpfs").sum()).alias("perc_cpfs")
    )
    .sort("qtd_cpfs", descending=True)
    .collect()
)
print("\n[FREQUÊNCIA — tipo_recarga_dominante]")
print(freq_tipo_rec)
# 6) FREQUÊNCIA — diversidade
freq_div_tipo_rec = (
    perfil_tipo_rec_cpf
    .group_by("qtd_tipos_recarga", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs") / pl.col("qtd_cpfs").sum()).alias("perc_cpfs")
    )
    .sort("qtd_tipos_recarga")
    .collect()
)
print("\n[FREQUÊNCIA — qtd_tipos_recarga]")
print(freq_div_tipo_rec)
# 7) CROSS — dominante × diversidade
cross_tipo_rec = (
    perfil_tipo_rec_cpf
    .group_by(["tipo_recarga_dominante", "qtd_tipos_recarga"], maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .sort(["tipo_recarga_dominante", "qtd_tipos_recarga"])
    .collect()
)
print("\n[CROSS — tipo_recarga_dominante × qtd_tipos_recarga]")
print(cross_tipo_rec)
#dimensão sem variabilidade útil

###################################
# PASSO 4.4 — BI_DIM_TIPO_RECARGA
###################################
# tipagem para join
eventos_com_bureau = (
    eventos_com_bureau
    .with_columns(
        pl.col("DW_TIPO_RECARGA")
        .cast(pl.Int64, strict=False)
        .alias("DW_TIPO_RECARGA")
    )
)
t0 = time.time()
# 1) Leitura e transformação da dimensão
dim_tipo_recarga = (
    pl.read_csv(
        r"C:\Users\cezar\Downloads\hackathon\bases_recarga\BI_DIM_TIPO_RECARGA.csv"
    )
    .select(["DW_TIPO_RECARGA"])
    .with_columns(
        pl.when(pl.col("DW_TIPO_RECARGA") < 0)
          .then(pl.lit("SEM_INFORMACAO"))
        .when(pl.col("DW_TIPO_RECARGA") == 1)
          .then(pl.lit("FRANQUIA"))
        .when(pl.col("DW_TIPO_RECARGA") == 2)
          .then(pl.lit("ADICIONAL"))
        .otherwise(pl.lit("SEM_INFORMACAO"))
        .alias("TIPO_RECARGA_NORMALIZADO")
    )
    .select(["DW_TIPO_RECARGA", "TIPO_RECARGA_NORMALIZADO"])
    .lazy()
)
# 2) Join com eventos
eventos_tipo_rec = (
    eventos_com_bureau
    .join(
        dim_tipo_recarga,
        on="DW_TIPO_RECARGA",
        how="left"
    )
)
# 3) Agregação por CPF
perfil_tipo_rec_cpf = (
    eventos_tipo_rec
    .group_by("NUM_CPF")
    .agg([
        pl.col("TIPO_RECARGA_NORMALIZADO")
          .drop_nulls()
          .mode()
          .first()
          .alias("tipo_recarga_dominante"),
        pl.col("TIPO_RECARGA_NORMALIZADO")
          .n_unique()
          .alias("qtd_tipos_recarga"),
    ])
)
print(f"[OK] BI_DIM_TIPO_RECARGA processada em {time.time() - t0:.2f}s")
# 4) CHECKS
checks_tipo_rec = (
    perfil_tipo_rec_cpf
    .select([
        pl.count().alias("cpfs_total"),
        pl.col("tipo_recarga_dominante")
          .filter(pl.col("tipo_recarga_dominante") == "SEM_INFORMACAO")
          .count()
          .alias("sem_informacao"),
        pl.col("qtd_tipos_recarga").max().alias("max_diversidade"),
    ])
    .collect()
)
print("\n[CHECKS — BI_DIM_TIPO_RECARGA]")
print(checks_tipo_rec)
# 5) FREQUÊNCIA — dominante
freq_tipo_rec = (
    perfil_tipo_rec_cpf
    .group_by("tipo_recarga_dominante", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs") / pl.col("qtd_cpfs").sum()).alias("perc_cpfs")
    )
    .sort("qtd_cpfs", descending=True)
    .collect()
)
print("\n[FREQUÊNCIA — tipo_recarga_dominante]")
print(freq_tipo_rec)
# 6) FREQUÊNCIA — diversidade
freq_div_tipo_rec = (
    perfil_tipo_rec_cpf
    .group_by("qtd_tipos_recarga", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs") / pl.col("qtd_cpfs").sum()).alias("perc_cpfs")
    )
    .sort("qtd_tipos_recarga")
    .collect()
)
print("\n[FREQUÊNCIA — qtd_tipos_recarga]")
print(freq_div_tipo_rec)
# 7) CROSS — dominante × diversidade
cross_tipo_rec = (
    perfil_tipo_rec_cpf
    .group_by(["tipo_recarga_dominante", "qtd_tipos_recarga"], maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .sort(["tipo_recarga_dominante", "qtd_tipos_recarga"])
    .collect()
)
print("\n[CROSS — tipo_recarga_dominante × qtd_tipos_recarga]")
print(cross_tipo_rec)
#dimensão sem variabilidade útil

###################################
# PASSO 4.5 — BI_DIM_FORMA_PAGAMENTO
###################################
# tipagem para join
eventos_com_bureau = (
    eventos_com_bureau
    .with_columns(
        pl.col("DW_FORMA_PAGAMENTO")
        .cast(pl.Int64, strict=False)
        .alias("DW_FORMA_PAGAMENTO")
    )
)
t0 = time.time()
# 1) Leitura e transformação da dimensão
dim_forma_pagamento = (
    pl.read_csv(
        r"C:\Users\cezar\Downloads\hackathon\bases_recarga\BI_DIM_FORMA_PAGAMENTO.csv"
    )
    .select(["DW_FORMA_PAGAMENTO"])
    .with_columns(
        pl.when(pl.col("DW_FORMA_PAGAMENTO") < 0)
          .then(pl.lit("SEM_INFORMACAO"))
        .when(pl.col("DW_FORMA_PAGAMENTO") == 11)
          .then(pl.lit("Credito de PrePago"))
        .when(pl.col("DW_FORMA_PAGAMENTO") == 12)
          .then(pl.lit("Debito Direto"))
        .when(pl.col("DW_FORMA_PAGAMENTO") == 13)
          .then(pl.lit("Pagamento Manual"))
        .when(pl.col("DW_FORMA_PAGAMENTO") == 14)
          .then(pl.lit("Arrecadacao Bancaria"))
        .when(pl.col("DW_FORMA_PAGAMENTO") == 10)
          .then(pl.lit("Pagamento Online"))
        .when(pl.col("DW_FORMA_PAGAMENTO") == 15)
          .then(pl.lit("ACORDO DE PAGAMENTO"))
        .otherwise(pl.lit("SEM_INFORMACAO"))
        .alias("FORMA_PAGAMENTO_NORMALIZADA")
    )
    .select(["DW_FORMA_PAGAMENTO", "FORMA_PAGAMENTO_NORMALIZADA"])
    .lazy()
)
# 2) Join com eventos
eventos_forma_pag = (
    eventos_com_bureau
    .join(
        dim_forma_pagamento,
        on="DW_FORMA_PAGAMENTO",
        how="left"
    )
)
# 3) Agregação por CPF
perfil_forma_pag_cpf = (
    eventos_forma_pag
    .group_by("NUM_CPF")
    .agg([
        pl.col("FORMA_PAGAMENTO_NORMALIZADA")
          .drop_nulls()
          .mode()
          .first()
          .alias("forma_pagamento_dominante"),
        pl.col("FORMA_PAGAMENTO_NORMALIZADA")
          .n_unique()
          .alias("qtd_formas_pagamento"),
    ])
)
print(f"[OK] BI_DIM_FORMA_PAGAMENTO processada em {time.time() - t0:.2f}s")
# 4) CHECKS
checks_forma_pag = (
    perfil_forma_pag_cpf
    .select([
        pl.count().alias("cpfs_total"),
        pl.col("forma_pagamento_dominante")
          .filter(pl.col("forma_pagamento_dominante") == "SEM_INFORMACAO")
          .count()
          .alias("sem_informacao"),
        pl.col("qtd_formas_pagamento").max().alias("max_diversidade"),
    ])
    .collect()
)
print("\n[CHECKS — BI_DIM_FORMA_PAGAMENTO]")
print(checks_forma_pag)
# 5) FREQUÊNCIA — dominante
freq_forma_pag = (
    perfil_forma_pag_cpf
    .group_by("forma_pagamento_dominante", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs") / pl.col("qtd_cpfs").sum()).alias("perc_cpfs")
    )
    .sort("qtd_cpfs", descending=True)
    .collect()
)
print("\n[FREQUÊNCIA — forma_pagamento_dominante]")
print(freq_forma_pag)
# 6) FREQUÊNCIA — diversidade
freq_div_forma_pag = (
    perfil_forma_pag_cpf
    .group_by("qtd_formas_pagamento", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs") / pl.col("qtd_cpfs").sum()).alias("perc_cpfs")
    )
    .sort("qtd_formas_pagamento")
    .collect()
)
print("\n[FREQUÊNCIA — qtd_formas_pagamento]")
print(freq_div_forma_pag)
# 7) CROSS — dominante × diversidade
cross_forma_pag = (
    perfil_forma_pag_cpf
    .group_by(["forma_pagamento_dominante", "qtd_formas_pagamento"], maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .sort(["forma_pagamento_dominante", "qtd_formas_pagamento"])
    .collect()
)
print("\n[CROSS — forma_pagamento_dominante × qtd_formas_pagamento]")
print(cross_forma_pag)

#BI_DIM_CANAL_AQUISICAO_CREDITO
#ignorada; nao traz novas variáveis

#BI com nomes de variaveis diferentes em relação a recarga atrasou e muito a análise até descobrir a falha
# ============================================================
# BLOCO 4.6 — BI_DIM_PLANO_PRECO
# PK: DW_PLANO
# Campos analíticos:
#   DSC_GRUPO_PLANO_BI -> GRUPO_PLANO
#   DSC_TIPO_PLANO_BI  -> TIPO_PLANO
#   IND_AMDOCS_PLAT_PRE -> FLAG_AMDOCS
#   COD_TECNOLOGIA_DW  -> TECNOLOGIA
# ============================================================

import polars as pl
import time

t0=time.time()

# 1) Leitura da dimensão (arquivo original)
dim_plano_preco=(
    pl.read_csv(
        r"C:\Users\cezar\Downloads\hackathon\bases_recarga\BI_DIM_PLANO_PRECO.csv",
        encoding="latin1",
        infer_schema_length=0
    )
    .select([
        "DW_PLANO",
        "DSC_GRUPO_PLANO_BI",
        "DSC_TIPO_PLANO_BI",
        "IND_AMDOCS_PLAT_PRE",
        "COD_TECNOLOGIA_DW"
    ])
    .with_columns(
        pl.col("DW_PLANO").cast(pl.Int64),
        pl.when(pl.col("DSC_GRUPO_PLANO_BI").is_null()|pl.col("DSC_GRUPO_PLANO_BI").cast(str).str.starts_with("-"))
          .then(pl.lit("SEM_INFORMACAO"))
          .otherwise(pl.col("DSC_GRUPO_PLANO_BI"))
          .alias("GRUPO_PLANO"),
        pl.when(pl.col("DSC_TIPO_PLANO_BI").is_null()|pl.col("DSC_TIPO_PLANO_BI").cast(str).str.starts_with("-"))
          .then(pl.lit("SEM_INFORMACAO"))
          .otherwise(pl.col("DSC_TIPO_PLANO_BI"))
          .alias("TIPO_PLANO"),
        pl.col("IND_AMDOCS_PLAT_PRE").alias("FLAG_AMDOCS"),
        pl.when(pl.col("COD_TECNOLOGIA_DW").is_null()|pl.col("COD_TECNOLOGIA_DW").cast(str).str.starts_with("-"))
          .then(pl.lit("SEM_INFORMACAO"))
          .otherwise(pl.col("COD_TECNOLOGIA_DW").cast(str))
          .alias("TECNOLOGIA")
    )
    .select(["DW_PLANO","GRUPO_PLANO","TIPO_PLANO","FLAG_AMDOCS","TECNOLOGIA"])
    .lazy()
)

# 2) Join eventos × dimensão
eventos_plano=(
    eventos_com_bureau
    .with_columns(pl.col("DW_PLANO").cast(pl.Int64))
    .join(dim_plano_preco,on="DW_PLANO",how="left")
)

# 3) Perfil por CPF
perfil_plano_cpf=(
    eventos_plano
    .group_by("NUM_CPF")
    .agg(
        pl.col("GRUPO_PLANO").n_unique().alias("qtd_grupos_plano"),
        pl.col("TIPO_PLANO").n_unique().alias("qtd_tipos_plano"),
        pl.col("GRUPO_PLANO").mode().first().alias("grupo_plano_dominante")
    )
)

print(f"[OK] BI_DIM_PLANO_PRECO processada em {round(time.time()-t0,2)}s")

# 4) CHECKS (executados separadamente para evitar erro de schema)
cpfs_total=perfil_plano_cpf.select(pl.len().alias("cpfs_total")).collect()
grupo_sem_info=perfil_plano_cpf.select((pl.col("grupo_plano_dominante")=="SEM_INFORMACAO").sum().alias("grupo_sem_informacao")).collect()
max_div_grupo=perfil_plano_cpf.select(pl.col("qtd_grupos_plano").max().alias("max_div_grupo")).collect()
max_div_tipo=perfil_plano_cpf.select(pl.col("qtd_tipos_plano").max().alias("max_div_tipo")).collect()

print("\n[CHECKS — BI_DIM_PLANO_PRECO]")
print(cpfs_total)
print(grupo_sem_info)
print(max_div_grupo)
print(max_div_tipo)

# 5) FREQUÊNCIAS — grupo_plano_dominante
freq_grupo_dominante=(
    perfil_plano_cpf
    .group_by("grupo_plano_dominante")
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("qtd_cpfs",descending=True)
    .collect()
)

# 6) FREQUÊNCIAS — qtd_grupos_plano
freq_qtd_grupos=(
    perfil_plano_cpf
    .group_by("qtd_grupos_plano")
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("qtd_grupos_plano")
    .collect()
)

print("\n[FREQUÊNCIA — grupo_plano_dominante]")
print(freq_grupo_dominante)

print("\n[FREQUÊNCIA — qtd_grupos_plano]")
print(freq_qtd_grupos)

###################################
# PASSO 4.7 — BI_DIM_PLATAFORMA
###################################
# tipagem para join
eventos_com_bureau = (
    eventos_com_bureau
    .with_columns(
        pl.col("COD_PLATAFORMA_ATU")
        .cast(pl.Utf8, strict=False)
        .alias("COD_PLATAFORMA_ATU")
    )
)
t0=time.time()
# 1) Leitura e transformação da dimensão
dim_plataforma=(
    pl.read_csv(
        r"C:\Users\cezar\Downloads\hackathon\bases_recarga\BI_DIM_PLATAFORMA.csv",
        encoding="latin1",
        infer_schema_length=0
    )
    .select([
        "COD_PLATAFORMA",
        "DSC_GRUPO_PLATAFORMA"
    ])
    .with_columns(
        pl.when(
            pl.col("COD_PLATAFORMA").is_null() |
            pl.col("DSC_GRUPO_PLATAFORMA").is_null() |
            pl.col("DSC_GRUPO_PLATAFORMA").cast(str).str.starts_with("-")
        )
        .then(pl.lit("SEM_INFORMACAO"))
        .otherwise(pl.col("DSC_GRUPO_PLATAFORMA"))
        .alias("PLATAFORMA_NORMALIZADA")
    )
    .select([
        pl.col("COD_PLATAFORMA").cast(pl.Utf8, strict=False),
        "PLATAFORMA_NORMALIZADA"
    ])
    .lazy()
)
# 2) Join com eventos
eventos_plataforma=(
    eventos_com_bureau
    .join(
        dim_plataforma,
        left_on="COD_PLATAFORMA_ATU",
        right_on="COD_PLATAFORMA",
        how="left"
    )
)
# 3) Agregação por CPF
perfil_plataforma_cpf=(
    eventos_plataforma
    .group_by("NUM_CPF")
    .agg([
        pl.col("PLATAFORMA_NORMALIZADA")
          .drop_nulls()
          .mode()
          .first()
          .alias("plataforma_dominante"),
        pl.col("PLATAFORMA_NORMALIZADA")
          .n_unique()
          .alias("qtd_plataformas"),
    ])
)
print(f"[OK] BI_DIM_PLATAFORMA processada em {round(time.time()-t0,2)}s")
# 4) CHECKS
checks_plataforma=(
    perfil_plataforma_cpf
    .select([
        pl.len().alias("cpfs_total"),
        pl.col("plataforma_dominante")
          .filter(pl.col("plataforma_dominante")=="SEM_INFORMACAO")
          .count()
          .alias("sem_informacao"),
        pl.col("qtd_plataformas").max().alias("max_diversidade"),
    ])
    .collect()
)
print("\n[CHECKS — BI_DIM_PLATAFORMA]")
print(checks_plataforma)
# 5) FREQUÊNCIA — dominante
freq_plataforma=(
    perfil_plataforma_cpf
    .group_by("plataforma_dominante", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("qtd_cpfs", descending=True)
    .collect()
)
print("\n[FREQUÊNCIA — plataforma_dominante]")
print(freq_plataforma)
# 6) FREQUÊNCIA — diversidade
freq_div_plataforma=(
    perfil_plataforma_cpf
    .group_by("qtd_plataformas", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("qtd_plataformas")
    .collect()
)
print("\n[FREQUÊNCIA — qtd_plataformas]")
print(freq_div_plataforma)
# 7) CROSS — dominante × diversidade
cross_plataforma=(
    perfil_plataforma_cpf
    .group_by(["plataforma_dominante","qtd_plataformas"], maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .sort(["plataforma_dominante","qtd_plataformas"])
    .collect()
)
print("\n[CROSS — plataforma_dominante × qtd_plataformas]")
print(cross_plataforma)
#inuitl

###################################
# PASSO 4.8 — BI_DIM_STATUS_PLATAFORMA
###################################
# tipagem para join
eventos_com_bureau=(
    eventos_com_bureau
    .with_columns(
        pl.col("COD_STATUS_PLATAFORMA")
        .cast(pl.Int64, strict=False)
        .alias("COD_STATUS_PLATAFORMA")
    )
)
t0=time.time()
# 1) Leitura e normalização da dimensão
dim_status_plataforma=(
    pl.read_csv(
        r"C:\Users\cezar\Downloads\hackathon\bases_recarga\BI_DIM_STATUS_PLATAFORMA.csv",
        encoding="latin1",
        infer_schema_length=0
    )
    .select(["COD_STATUS_PLATAFORMA","IND_ATIVO"])
    .with_columns(
        pl.col("COD_STATUS_PLATAFORMA")
        .cast(pl.Int64, strict=False)
        .alias("COD_STATUS_PLATAFORMA")
    )
    .with_columns(
        pl.when(
            pl.col("COD_STATUS_PLATAFORMA").is_null()|
            (pl.col("COD_STATUS_PLATAFORMA")<0)|
            pl.col("IND_ATIVO").is_null()
        )
        .then(pl.lit("SEM_INFORMACAO"))
        .otherwise(pl.col("IND_ATIVO").cast(str))
        .alias("STATUS_PLATAFORMA_NORMALIZADO")
    )
    .select(["COD_STATUS_PLATAFORMA","STATUS_PLATAFORMA_NORMALIZADO"])
    .lazy()
)
# 2) Join com eventos
eventos_status_plat=(
    eventos_com_bureau
    .join(
        dim_status_plataforma,
        on="COD_STATUS_PLATAFORMA",
        how="left"
    )
)
# 3) Agregação por CPF
perfil_status_plat_cpf=(
    eventos_status_plat
    .group_by("NUM_CPF")
    .agg([
        pl.col("STATUS_PLATAFORMA_NORMALIZADO")
          .drop_nulls()
          .mode()
          .first()
          .alias("status_plataforma_dominante"),
        pl.col("STATUS_PLATAFORMA_NORMALIZADO")
          .n_unique()
          .alias("qtd_status_plataforma")
    ])
)
print(f"[OK] BI_DIM_STATUS_PLATAFORMA processada em {time.time()-t0:.2f}s")
# 4) CHECKS
checks_status_plat=(
    perfil_status_plat_cpf
    .select(
        pl.len().alias("cpfs_total"),
        (pl.col("status_plataforma_dominante")=="SEM_INFORMACAO").sum().alias("sem_informacao"),
        pl.col("qtd_status_plataforma").max().alias("max_diversidade")
    )
    .collect()
)
print("\n[CHECKS — BI_DIM_STATUS_PLATAFORMA]")
print(checks_status_plat)
# 5) FREQUÊNCIA — dominante
freq_status_plat=(
    perfil_status_plat_cpf
    .group_by("status_plataforma_dominante", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("qtd_cpfs", descending=True)
    .collect()
)
print("\n[FREQUÊNCIA — status_plataforma_dominante]")
print(freq_status_plat)
# 6) FREQUÊNCIA — diversidade
freq_div_status_plat=(
    perfil_status_plat_cpf
    .group_by("qtd_status_plataforma", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("qtd_status_plataforma")
    .collect()
)
print("\n[FREQUÊNCIA — qtd_status_plataforma]")
print(freq_div_status_plat)
# 7) CROSS — dominante × diversidade
cross_status_plat=(
    perfil_status_plat_cpf
    .group_by(["status_plataforma_dominante","qtd_status_plataforma"], maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .sort(["status_plataforma_dominante","qtd_status_plataforma"])
    .collect()
)
print("\n[CROSS — status_plataforma_dominante × qtd_status_plataforma]")
print(cross_status_plat)

###################################
# PASSO 4.9 — BI_DIM_FORMA_PAGAMENTO
###################################
# tipagem para join
eventos_com_bureau=(
    eventos_com_bureau
    .with_columns(
        pl.col("DW_FORMA_PAGAMENTO")
        .cast(pl.Int64, strict=False)
        .alias("DW_FORMA_PAGAMENTO")
    )
)
t0=time.time()
# 1) Leitura e normalização da dimensão
dim_forma_pagamento=(
    pl.read_csv(
        r"C:\Users\cezar\Downloads\hackathon\bases_recarga\BI_DIM_FORMA_PAGAMENTO.csv",
        encoding="latin1",
        infer_schema_length=0
    )
    .select([
        "COD_FORMA_PAGAMENTO",
        "DSC_FORMA_PAGAMENTO"
    ])
    .with_columns(
        pl.col("COD_FORMA_PAGAMENTO")
        .cast(pl.Int64, strict=False)
        .alias("COD_FORMA_PAGAMENTO")
    )
    .with_columns(
        pl.when(
            pl.col("COD_FORMA_PAGAMENTO").is_null() |
            (pl.col("COD_FORMA_PAGAMENTO") < 0) |
            pl.col("DSC_FORMA_PAGAMENTO").is_null() |
            pl.col("DSC_FORMA_PAGAMENTO").cast(str).str.starts_with("-")
        )
        .then(pl.lit("SEM_INFORMACAO"))
        .otherwise(pl.col("DSC_FORMA_PAGAMENTO").cast(str))
        .alias("FORMA_PAGAMENTO_NORMALIZADA")
    )
    .select([
        "COD_FORMA_PAGAMENTO",
        "FORMA_PAGAMENTO_NORMALIZADA"
    ])
    .lazy()
)
# 2) Join com eventos
eventos_forma_pagamento=(
    eventos_com_bureau
    .join(
        dim_forma_pagamento,
        left_on="DW_FORMA_PAGAMENTO",
        right_on="COD_FORMA_PAGAMENTO",
        how="left"
    )
)
# 3) Agregação por CPF
perfil_forma_pagamento_cpf=(
    eventos_forma_pagamento
    .group_by("NUM_CPF")
    .agg([
        pl.col("FORMA_PAGAMENTO_NORMALIZADA")
          .drop_nulls()
          .mode()
          .first()
          .alias("forma_pagamento_dominante"),
        pl.col("FORMA_PAGAMENTO_NORMALIZADA")
          .n_unique()
          .alias("qtd_formas_pagamento")
    ])
)
print(f"[OK] BI_DIM_FORMA_PAGAMENTO processada em {time.time()-t0:.2f}s")
# 4) CHECKS
checks_forma_pagamento=(
    perfil_forma_pagamento_cpf
    .select(
        pl.len().alias("cpfs_total"),
        (pl.col("forma_pagamento_dominante")=="SEM_INFORMACAO")
            .sum()
            .alias("sem_informacao"),
        pl.col("qtd_formas_pagamento")
            .max()
            .alias("max_diversidade")
    )
    .collect()
)
print("\n[CHECKS — BI_DIM_FORMA_PAGAMENTO]")
print(checks_forma_pagamento)
# 5) FREQUÊNCIA — dominante
freq_forma_pagamento=(
    perfil_forma_pagamento_cpf
    .group_by("forma_pagamento_dominante", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("qtd_cpfs", descending=True)
    .collect()
)
print("\n[FREQUÊNCIA — forma_pagamento_dominante]")
print(freq_forma_pagamento)
# 6) FREQUÊNCIA — diversidade
freq_div_forma_pagamento=(
    perfil_forma_pagamento_cpf
    .group_by("qtd_formas_pagamento", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("qtd_formas_pagamento")
    .collect()
)
print("\n[FREQUÊNCIA — qtd_formas_pagamento]")
print(freq_div_forma_pagamento)
# 7) CROSS — dominante × diversidade
cross_forma_pagamento=(
    perfil_forma_pagamento_cpf
    .group_by(
        ["forma_pagamento_dominante","qtd_formas_pagamento"],
        maintain_order=True
    )
    .agg(pl.len().alias("qtd_cpfs"))
    .sort(["forma_pagamento_dominante","qtd_formas_pagamento"])
    .collect()
)
print("\n[CROSS — forma_pagamento_dominante × qtd_formas_pagamento]")
print(cross_forma_pagamento)
#inutil

###################################
# PASSO 4.10 — BI_DIM_TECNOLOGIA
###################################
# tipagem para join
eventos_com_bureau=(
    eventos_com_bureau
    .with_columns(
        pl.col("COD_TECNOLOGIA_DW")
        .cast(pl.Int64, strict=False)
        .alias("COD_TECNOLOGIA_DW")
    )
)
t0=time.time()
# 1) Leitura e normalização da dimensão
dim_tecnologia=(
    pl.read_csv(
        r"C:\Users\cezar\Downloads\hackathon\bases_recarga\BI_DIM_TECNOLOGIA.csv",
        encoding="latin1",
        infer_schema_length=0
    )
    .select(["COD_TECNOLOGIA_DW"])
    .with_columns(
        pl.col("COD_TECNOLOGIA_DW")
        .cast(pl.Int64, strict=False)
        .alias("COD_TECNOLOGIA_DW")
    )
    .with_columns(
        pl.when(
            pl.col("COD_TECNOLOGIA_DW").is_null()|
            (pl.col("COD_TECNOLOGIA_DW")<0)
        )
        .then(pl.lit("SEM_INFORMACAO"))
        .otherwise(pl.col("COD_TECNOLOGIA_DW").cast(str))
        .alias("TECNOLOGIA_NORMALIZADA")
    )
    .select(["COD_TECNOLOGIA_DW","TECNOLOGIA_NORMALIZADA"])
    .lazy()
)
# 2) Join com eventos
eventos_tecnologia=(
    eventos_com_bureau
    .join(
        dim_tecnologia,
        on="COD_TECNOLOGIA_DW",
        how="left"
    )
)
# 3) Agregação por CPF
perfil_tecnologia_cpf=(
    eventos_tecnologia
    .group_by("NUM_CPF")
    .agg([
        pl.col("TECNOLOGIA_NORMALIZADA")
          .drop_nulls()
          .mode()
          .first()
          .alias("tecnologia_dominante"),
        pl.col("TECNOLOGIA_NORMALIZADA")
          .n_unique()
          .alias("qtd_tecnologias")
    ])
)
print(f"[OK] BI_DIM_TECNOLOGIA processada em {time.time()-t0:.2f}s")
# 4) CHECKS
checks_tecnologia=(
    perfil_tecnologia_cpf
    .select(
        pl.len().alias("cpfs_total"),
        (pl.col("tecnologia_dominante")=="SEM_INFORMACAO").sum().alias("sem_informacao"),
        pl.col("qtd_tecnologias").max().alias("max_diversidade")
    )
    .collect()
)
print("\n[CHECKS — BI_DIM_TECNOLOGIA]")
print(checks_tecnologia)
# 5) FREQUÊNCIA — dominante
freq_tecnologia=(
    perfil_tecnologia_cpf
    .group_by("tecnologia_dominante", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("qtd_cpfs", descending=True)
    .collect()
)
print("\n[FREQUÊNCIA — tecnologia_dominante]")
print(freq_tecnologia)
# 6) FREQUÊNCIA — diversidade
freq_div_tecnologia=(
    perfil_tecnologia_cpf
    .group_by("qtd_tecnologias", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("qtd_tecnologias")
    .collect()
)
print("\n[FREQUÊNCIA — qtd_tecnologias]")
print(freq_div_tecnologia)
# 7) CROSS — dominante × diversidade
cross_tecnologia=(
    perfil_tecnologia_cpf
    .group_by(["tecnologia_dominante","qtd_tecnologias"], maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .sort(["tecnologia_dominante","qtd_tecnologias"])
    .collect()
)
print("\n[CROSS — tecnologia_dominante × qtd_tecnologias]")
print(cross_tecnologia)
#inutil

###################################
# PASSO 4.11 — BI_DIM_TIPO_CREDITO
###################################
# tipagem para join
eventos_com_bureau=(
    eventos_com_bureau
    .with_columns(
        pl.col("COD_TIPO_CREDITO")
        .cast(pl.Utf8, strict=False)
        .alias("COD_TIPO_CREDITO")
    )
)
t0=time.time()
# 1) Leitura e normalização da dimensão
dim_tipo_credito=(
    pl.read_csv(
        r"C:\Users\cezar\Downloads\hackathon\bases_recarga\BI_DIM_TIPO_CREDITO.csv",
        encoding="latin1",
        infer_schema_length=0
    )
    .select(["COD_TIPO_CREDITO"])
    .with_columns(
        pl.when(
            pl.col("COD_TIPO_CREDITO").is_null()|
            pl.col("COD_TIPO_CREDITO").is_in(["-1","-2","-3"])
        )
        .then(pl.lit("SEM_INFORMACAO"))
        .when(pl.col("COD_TIPO_CREDITO")=="PE")
        .then(pl.lit("ONLINE"))
        .when(pl.col("COD_TIPO_CREDITO")=="AU")
        .then(pl.lit("AUTOCONTROLE"))
        .when(pl.col("COD_TIPO_CREDITO")=="BO")
        .then(pl.lit("BONUS"))
        .when(pl.col("COD_TIPO_CREDITO")=="CF")
        .then(pl.lit("CARTAO_FISICO"))
        .when(pl.col("COD_TIPO_CREDITO")=="CV")
        .then(pl.lit("PIN_ELETRONICO"))
        .when(pl.col("COD_TIPO_CREDITO")=="IO")
        .then(pl.lit("IOIO"))
        .when(pl.col("COD_TIPO_CREDITO").is_in(["TE","TF"]))
        .then(pl.lit("TRANSFERENCIA"))
        .otherwise(pl.lit("OUTROS"))
        .alias("TIPO_CREDITO_NORMALIZADO")
    )
    .select(["COD_TIPO_CREDITO","TIPO_CREDITO_NORMALIZADO"])
    .lazy()
)
# 2) Join com eventos
eventos_tipo_credito=(
    eventos_com_bureau
    .join(
        dim_tipo_credito,
        on="COD_TIPO_CREDITO",
        how="left"
    )
)
# 3) Agregação por CPF
perfil_tipo_credito_cpf=(
    eventos_tipo_credito
    .group_by("NUM_CPF")
    .agg([
        pl.col("TIPO_CREDITO_NORMALIZADO")
          .drop_nulls()
          .mode()
          .first()
          .alias("tipo_credito_dominante"),
        pl.col("TIPO_CREDITO_NORMALIZADO")
          .n_unique()
          .alias("qtd_tipos_credito")
    ])
)
print(f"[OK] BI_DIM_TIPO_CREDITO processada em {time.time()-t0:.2f}s")
# 4) CHECKS
checks_tipo_credito=(
    perfil_tipo_credito_cpf
    .select(
        pl.len().alias("cpfs_total"),
        (pl.col("tipo_credito_dominante")=="SEM_INFORMACAO").sum().alias("sem_informacao"),
        pl.col("qtd_tipos_credito").max().alias("max_diversidade")
    )
    .collect()
)
print("\n[CHECKS — BI_DIM_TIPO_CREDITO]")
print(checks_tipo_credito)
# 5) FREQUÊNCIA — dominante
freq_tipo_credito=(
    perfil_tipo_credito_cpf
    .group_by("tipo_credito_dominante", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("qtd_cpfs", descending=True)
    .collect()
)
print("\n[FREQUÊNCIA — tipo_credito_dominante]")
print(freq_tipo_credito)
# 6) FREQUÊNCIA — diversidade
freq_div_tipo_credito=(
    perfil_tipo_credito_cpf
    .group_by("qtd_tipos_credito", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("qtd_tipos_credito")
    .collect()
)
print("\n[FREQUÊNCIA — qtd_tipos_credito]")
print(freq_div_tipo_credito)
# 7) CROSS — dominante × diversidade
cross_tipo_credito=(
    perfil_tipo_credito_cpf
    .group_by(["tipo_credito_dominante","qtd_tipos_credito"], maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .sort(["tipo_credito_dominante","qtd_tipos_credito"])
    .collect()
)
print("\n[CROSS — tipo_credito_dominante × qtd_tipos_credito]")
print(cross_tipo_credito)
#inutil

######
#todas dimensoes checadas, somente a primeira agregou

# retornando à base RECARGA para criação de VARs
# decidi ignorar variáveis monetárias até entender valores negativos
# seguem sugestões minhas e do GPT 5.2

###################################
# BLOCO A — VOLUME ABSOLUTO
###################################
t0=time.time()
# 0) Garantia de tipagem da data
eventos_base=(
    eventos_com_bureau
    .with_columns(
        pl.col("DAT_INSERCAO_CREDITO")
        .cast(pl.Date, strict=False)
        .alias("DAT_INSERCAO_CREDITO")
    )
)
# 1) Referência temporal
data_ref=(
    eventos_base
    .select(pl.col("DAT_INSERCAO_CREDITO").max())
    .collect()
    .item()
)
# 2) Flags temporais por evento
eventos_flags=(
    eventos_base
    .with_columns([
        (pl.col("DAT_INSERCAO_CREDITO")>=pl.lit(data_ref-timedelta(days=30))).alias("flag_30d"),
        (pl.col("DAT_INSERCAO_CREDITO")>=pl.lit(data_ref-timedelta(days=60))).alias("flag_60d"),
        (pl.col("DAT_INSERCAO_CREDITO")>=pl.lit(data_ref-timedelta(days=90))).alias("flag_90d")
    ])
)
# 3) Agregação por CPF — volume absoluto
perfil_volume_cpf=(
    eventos_flags
    .group_by("NUM_CPF")
    .agg([
        pl.len().alias("evt_qtd_total"),
        pl.col("flag_30d").sum().alias("evt_qtd_30d"),
        pl.col("flag_60d").sum().alias("evt_qtd_60d"),
        pl.col("flag_90d").sum().alias("evt_qtd_90d")
    ])
)
# 4) Proporções temporais
perfil_volume_cpf=(
    perfil_volume_cpf
    .with_columns([
        pl.when(pl.col("evt_qtd_total")>0)
          .then(pl.col("evt_qtd_30d")/pl.col("evt_qtd_total"))
          .otherwise(0)
          .alias("evt_share_30d"),
        pl.when(pl.col("evt_qtd_total")>0)
          .then(pl.col("evt_qtd_60d")/pl.col("evt_qtd_total"))
          .otherwise(0)
          .alias("evt_share_60d"),
        pl.when(pl.col("evt_qtd_total")>0)
          .then(pl.col("evt_qtd_90d")/pl.col("evt_qtd_total"))
          .otherwise(0)
          .alias("evt_share_90d")
    ])
    .lazy()
)
print(f"[OK] BLOCO A — VOLUME ABSOLUTO processado em {time.time()-t0:.2f}s")
# 5) CHECKS — SANIDADE
checks_volume=(
    perfil_volume_cpf
    .select(
        pl.len().alias("cpfs_total"),
        pl.col("evt_qtd_total").min().alias("min_evt_total"),
        pl.col("evt_qtd_total").max().alias("max_evt_total"),
        pl.col("evt_qtd_30d").max().alias("max_evt_30d"),
        pl.col("evt_qtd_60d").max().alias("max_evt_60d"),
        pl.col("evt_qtd_90d").max().alias("max_evt_90d")
    )
    .collect()
)
print("\n[CHECKS — BLOCO A | VOLUME]")
print(checks_volume)
# 6) DISTRIBUIÇÃO — evt_qtd_total
dist_evt_total=(
    perfil_volume_cpf
    .select("evt_qtd_total")
    .group_by("evt_qtd_total")
    .agg(pl.len().alias("qtd_cpfs"))
    .sort("evt_qtd_total")
    .collect()
)
print("\n[DISTRIBUIÇÃO — evt_qtd_total]")
print(dist_evt_total.head(20))


###################################
# BLOCO B — RECÊNCIA E RITMO
###################################
t0=time.time()
# 1) Agregação temporal básica por CPF
perfil_tempo_cpf=(
    eventos_com_bureau
    .group_by("NUM_CPF")
    .agg([
        pl.col("DAT_INSERCAO_CREDITO").min().alias("dt_primeiro_evt"),
        pl.col("DAT_INSERCAO_CREDITO").max().alias("dt_ultimo_evt"),
        pl.len().alias("evt_qtd_total")
    ])
)
# 2) Métricas temporais derivadas
perfil_tempo_cpf=(
    perfil_tempo_cpf
    .with_columns([
        (pl.col("dt_ultimo_evt")-pl.col("dt_primeiro_evt"))
            .dt.total_days()
            .alias("vida_ativa_dias"),
        (pl.lit(data_ref)-pl.col("dt_ultimo_evt"))
            .dt.total_days()
            .alias("dias_desde_ultimo_evt")
    ])
    .with_columns([
        pl.when(pl.col("vida_ativa_dias")>0)
          .then(pl.col("evt_qtd_total")/pl.col("vida_ativa_dias"))
          .otherwise(pl.col("evt_qtd_total"))
          .alias("ritmo_medio_evt"),
        pl.when(pl.col("evt_qtd_total")>1)
          .then(pl.col("vida_ativa_dias")/(pl.col("evt_qtd_total")-1))
          .otherwise(None)
          .alias("gap_medio_evt_dias")
    ])
    .lazy()
)
print(f"[OK] BLOCO B — RECÊNCIA E RITMO processado em {time.time()-t0:.2f}s")
# 3) CHECKS — SANIDADE
checks_tempo=(
    perfil_tempo_cpf
    .select(
        pl.len().alias("cpfs_total"),
        pl.col("dias_desde_ultimo_evt").min().alias("min_recencia"),
        pl.col("dias_desde_ultimo_evt").max().alias("max_recencia"),
        pl.col("vida_ativa_dias").max().alias("max_vida_ativa"),
        pl.col("ritmo_medio_evt").max().alias("max_ritmo_evt")
    )
    .collect()
)
print("\n[CHECKS — BLOCO B | RECÊNCIA]")
print(checks_tempo)


###################################
# BLOCO C — ESTABILIDADE vs RUPTURA TEMPORAL
###################################
t0=time.time()
# 0) Referência temporal
data_ref=(
    eventos_com_bureau
    .select(pl.col("DAT_INSERCAO_CREDITO").max())
    .collect()
    .item()
)
# 1) Eventos com flags temporais
eventos_c=(
    eventos_com_bureau
    .with_columns([
        (pl.col("DAT_INSERCAO_CREDITO")>=pl.lit(data_ref-timedelta(days=30))).alias("flag_30d"),
        (pl.col("DAT_INSERCAO_CREDITO")>=pl.lit(data_ref-timedelta(days=60))).alias("flag_60d"),
        (pl.col("DAT_INSERCAO_CREDITO")>=pl.lit(data_ref-timedelta(days=90))).alias("flag_90d")
    ])
)
# 2) Agregação base por CPF
perfil_burst_cpf=(
    eventos_c
    .group_by("NUM_CPF")
    .agg([
        pl.len().alias("evt_qtd_total"),
        pl.col("flag_30d").sum().alias("evt_qtd_30d"),
        pl.col("flag_60d").sum().alias("evt_qtd_60d"),
        pl.col("flag_90d").sum().alias("evt_qtd_90d"),
        pl.col("DAT_INSERCAO_CREDITO").min().alias("dt_primeiro_evt"),
        pl.col("DAT_INSERCAO_CREDITO").max().alias("dt_ultimo_evt")
    ])
)
# 3) Vida ativa
perfil_burst_cpf=(
    perfil_burst_cpf
    .with_columns(
        (pl.col("dt_ultimo_evt")-pl.col("dt_primeiro_evt"))
        .dt.total_days()
        .alias("vida_ativa_dias")
    )
)
# 4) Métricas de concentração e ritmo
perfil_burst_cpf=(
    perfil_burst_cpf
    .with_columns([
        (pl.col("evt_qtd_30d")/pl.col("evt_qtd_total")).fill_null(0).alias("share_evt_30d"),
        (pl.col("evt_qtd_60d")/pl.col("evt_qtd_total")).fill_null(0).alias("share_evt_60d"),
        (pl.col("evt_qtd_90d")/pl.col("evt_qtd_total")).fill_null(0).alias("share_evt_90d"),
        (pl.col("evt_qtd_30d")/(pl.col("vida_ativa_dias")+1)).fill_null(0).alias("ritmo_30d")
    ])
    .lazy()
)
print(f"[OK] BLOCO C processado em {time.time()-t0:.2f}s")
# 5) CHECKS
checks_burst=(
    perfil_burst_cpf
    .select(
        pl.len().alias("cpfs_total"),
        pl.col("share_evt_30d").max().alias("max_share_30d"),
        pl.col("share_evt_60d").max().alias("max_share_60d"),
        pl.col("share_evt_90d").max().alias("max_share_90d"),
        pl.col("ritmo_30d").max().alias("max_ritmo_30d")
    )
    .collect()
)
print("\n[CHECKS — BLOCO C | BURST]")
print(checks_burst)

###################################
# BLOCO D — REGULARIDADE / ESPAÇAMENTO ENTRE EVENTOS
###################################
t0=time.time()
# 0) Colunas mínimas (checagem leve, sem collect_schema)
cols_min=["NUM_CPF","DAT_INSERCAO_CREDITO"]
missing=[c for c in cols_min if c not in eventos_com_bureau.columns]
if len(missing)>0:
    raise ValueError(f"Colunas ausentes em eventos_com_bureau: {missing}")
# 1) Base ordenada + gaps (diferença entre eventos consecutivos por CPF)
eventos_gaps=(
    eventos_com_bureau
    .select(["NUM_CPF","DAT_INSERCAO_CREDITO"])
    .sort(["NUM_CPF","DAT_INSERCAO_CREDITO"])
    .with_columns(
        (pl.col("DAT_INSERCAO_CREDITO")
         .diff()
         .over("NUM_CPF"))
        .alias("gap_raw")
    )
    .with_columns(
        pl.col("gap_raw")
        .dt.total_days()
        .cast(pl.Float64, strict=False)
        .alias("gap_dias")
    )
    .drop(["gap_raw"])
)
# 2) Agregação por CPF — regularidade/espacamento
perfil_reg_cpf=(
    eventos_gaps
    .group_by("NUM_CPF")
    .agg([
        pl.len().alias("evt_qtd_total"),
        pl.col("gap_dias").drop_nulls().len().alias("qtd_gaps_validos"),
        pl.col("gap_dias").mean().alias("gap_media_dias"),
        pl.col("gap_dias").median().alias("gap_mediana_dias"),
        pl.col("gap_dias").std().alias("gap_dp_dias"),
        pl.col("gap_dias").min().alias("gap_min_dias"),
        pl.col("gap_dias").max().alias("gap_max_dias"),
        pl.col("gap_dias").quantile(0.9, "nearest").alias("gap_p90_dias"),
        (pl.col("gap_dias")<=1).sum().alias("qtd_gaps_le_1d"),
        (pl.col("gap_dias")<=3).sum().alias("qtd_gaps_le_3d"),
        (pl.col("gap_dias")<=7).sum().alias("qtd_gaps_le_7d")
    ])
    .with_columns([
        pl.when(pl.col("qtd_gaps_validos")>0)
          .then(pl.col("qtd_gaps_le_1d")/pl.col("qtd_gaps_validos"))
          .otherwise(0)
          .alias("share_gaps_le_1d"),
        pl.when(pl.col("qtd_gaps_validos")>0)
          .then(pl.col("qtd_gaps_le_3d")/pl.col("qtd_gaps_validos"))
          .otherwise(0)
          .alias("share_gaps_le_3d"),
        pl.when(pl.col("qtd_gaps_validos")>0)
          .then(pl.col("qtd_gaps_le_7d")/pl.col("qtd_gaps_validos"))
          .otherwise(0)
          .alias("share_gaps_le_7d"),
        pl.when((pl.col("gap_media_dias")>0) & pl.col("gap_dp_dias").is_not_null())
          .then(pl.col("gap_dp_dias")/pl.col("gap_media_dias"))
          .otherwise(None)
          .alias("cv_gap_dias"),
        pl.when(pl.col("gap_dp_dias").is_not_null() & pl.col("gap_media_dias").is_not_null() & ((pl.col("gap_dp_dias")+pl.col("gap_media_dias"))>0))
          .then((pl.col("gap_dp_dias")-pl.col("gap_media_dias"))/(pl.col("gap_dp_dias")+pl.col("gap_media_dias")))
          .otherwise(None)
          .alias("burstiness_gap")
    ])
    .lazy()
)
print(f"[OK] BLOCO D — REGULARIDADE/ESPAÇAMENTO processado em {time.time()-t0:.2f}s")
# 3) CHECKS GERAIS
checks_reg=(
    perfil_reg_cpf
    .select(
        pl.len().alias("cpfs_total"),
        (pl.col("qtd_gaps_validos")==0).sum().alias("cpfs_sem_gaps"),
        pl.col("gap_media_dias").max().alias("max_gap_media"),
        pl.col("gap_max_dias").max().alias("max_gap_max"),
        pl.col("cv_gap_dias").max().alias("max_cv_gap"),
        pl.col("share_gaps_le_1d").max().alias("max_share_le_1d")
    )
    .collect()
)
print("\n[CHECKS — BLOCO D | REGULARIDADE]")
print(checks_reg)
# 4) DISTRIBUIÇÃO — cv_gap_dias (faixas)
dist_cv_gap=(
    perfil_reg_cpf
    .with_columns(
        pl.when(pl.col("cv_gap_dias").is_null()).then(pl.lit("NULL/NA"))
        .when(pl.col("cv_gap_dias")<=0.25).then(pl.lit("≤0.25 (muito regular)"))
        .when(pl.col("cv_gap_dias")<=0.75).then(pl.lit("0.25–0.75 (regular)"))
        .when(pl.col("cv_gap_dias")<=1.50).then(pl.lit("0.75–1.50 (irregular)"))
        .otherwise(pl.lit(">1.50 (muito irregular)"))
        .alias("faixa_cv_gap")
    )
    .group_by("faixa_cv_gap", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("qtd_cpfs", descending=True)
    .collect()
)
print("\n[DISTRIBUIÇÃO — cv_gap_dias]")
print(dist_cv_gap)
# 5) DISTRIBUIÇÃO — share_gaps_le_1d (faixas)
dist_share_le_1d=(
    perfil_reg_cpf
    .with_columns(
        pl.when(pl.col("share_gaps_le_1d")==0).then(pl.lit("0%"))
        .when(pl.col("share_gaps_le_1d")<=0.25).then(pl.lit("0–25%"))
        .when(pl.col("share_gaps_le_1d")<=0.50).then(pl.lit("25–50%"))
        .when(pl.col("share_gaps_le_1d")<=0.75).then(pl.lit("50–75%"))
        .otherwise(pl.lit(">75%"))
        .alias("faixa_share_le_1d")
    )
    .group_by("faixa_share_le_1d", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("faixa_share_le_1d")
    .collect()
)
print("\n[DISTRIBUIÇÃO — share_gaps_le_1d]")
print(dist_share_le_1d)
# 6) CROSS — regularidade (cv) × concentração de gaps curtos (share<=1d)
cross_reg=(
    perfil_reg_cpf
    .with_columns([
        pl.when(pl.col("cv_gap_dias").is_null()).then(pl.lit("NA"))
        .when(pl.col("cv_gap_dias")<=0.75).then(pl.lit("REGULAR"))
        .otherwise(pl.lit("IRREGULAR"))
        .alias("nivel_reg"),
        pl.when(pl.col("share_gaps_le_1d")<=0.25).then(pl.lit("BAIXA"))
        .when(pl.col("share_gaps_le_1d")<=0.75).then(pl.lit("MEDIA"))
        .otherwise(pl.lit("ALTA"))
        .alias("nivel_gap_curto")
    ])
    .group_by(["nivel_reg","nivel_gap_curto"], maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort(["nivel_reg","nivel_gap_curto"])
    .collect()
)
print("\n[CROSS — regularidade (cv) × share gaps ≤1d]")
print(cross_reg)


###################################
# BLOCO E — INTENSIDADE E EXTREMOS
###################################
t0=time.time()

# 1) Volume diário por CPF
evt_por_dia=(
    eventos_com_bureau
    .group_by(["NUM_CPF","DAT_INSERCAO_CREDITO"])
    .agg(pl.len().alias("evt_dia"))
)

# 2) Métricas de intensidade por CPF
perfil_intensidade_cpf=(
    evt_por_dia
    .group_by("NUM_CPF")
    .agg([
        pl.col("evt_dia").max().alias("evt_max_dia"),
        pl.col("evt_dia").mean().alias("evt_mean_dia"),
        pl.col("evt_dia").sum().alias("evt_qtd_total"),
        pl.len().alias("dias_ativos")
    ])
    .with_columns([
        (pl.col("evt_max_dia")/pl.col("evt_mean_dia"))
            .fill_nan(0)
            .fill_null(0)
            .alias("ratio_pico_media"),

        (pl.col("evt_max_dia")/pl.col("evt_qtd_total"))
            .fill_nan(0)
            .fill_null(0)
            .alias("share_pico_total"),

        pl.when(pl.col("evt_max_dia")>=10)
          .then(1)
          .otherwise(0)
          .alias("flag_super_pico")
    ])
    .lazy()
)

# >>> MATERIALIZAÇÃO ÚNICA (OBRIGATÓRIA) <<<
perfil_intensidade_cpf = perfil_intensidade_cpf.collect().lazy()

print(f"[OK] BLOCO E processado em {time.time()-t0:.2f}s")

# 3) CHECKS
checks_intensidade=(
    perfil_intensidade_cpf
    .select(
        pl.len().alias("cpfs_total"),
        pl.col("evt_max_dia").max().alias("max_evt_dia"),
        pl.col("ratio_pico_media").max().alias("max_ratio_pico"),
        pl.col("share_pico_total").max().alias("max_share_pico"),
        pl.col("flag_super_pico").sum().alias("cpfs_super_pico")
    )
    .collect()
)

print("\n[CHECKS — BLOCO E | INTENSIDADE]")
print(checks_intensidade)

# 4) DISTRIBUIÇÃO — ratio pico / média
dist_ratio_pico=(
    perfil_intensidade_cpf
    .with_columns(
        pl.when(pl.col("ratio_pico_media")<=2).then(pl.lit("≤2 (leve)"))
        .when(pl.col("ratio_pico_media")<=5).then(pl.lit("2–5 (moderado)"))
        .when(pl.col("ratio_pico_media")<=10).then(pl.lit("5–10 (alto)"))
        .otherwise(pl.lit(">10 (extremo)"))
        .alias("faixa_ratio_pico")
    )
    .group_by("faixa_ratio_pico", maintain_order=True)
    .agg(pl.len().alias("qtd_cpfs"))
    .with_columns(
        (pl.col("qtd_cpfs")/pl.col("qtd_cpfs").sum()).alias("pct_cpfs")
    )
    .sort("faixa_ratio_pico")
    .collect()
)
print(dist_ratio_pico)


###################################
# BLOCO F — INTEGRAÇÃO FINAL A–E
###################################
t0 = time.time()

perfil_final_cpf = (
    perfil_volume_cpf

    # BLOCO B — recência e ritmo
    .join(
        perfil_tempo_cpf.select([
            "NUM_CPF",
            "vida_ativa_dias",
            "dias_desde_ultimo_evt",
            "ritmo_medio_evt",
            "gap_medio_evt_dias"
        ]),
        on="NUM_CPF",
        how="left"
    )

    # BLOCO C — burst / concentração recente
    .join(
        perfil_burst_cpf.select([
            "NUM_CPF",
            "share_evt_30d",
            "share_evt_60d",
            "share_evt_90d",
            "ritmo_30d"
        ]),
        on="NUM_CPF",
        how="left"
    )

    # BLOCO D — regularidade / espaçamento
    .join(
        perfil_reg_cpf.select([
            "NUM_CPF",
            "gap_media_dias",
            "gap_mediana_dias",
            "gap_dp_dias",
            "gap_min_dias",
            "gap_max_dias",
            "gap_p90_dias",
            "share_gaps_le_1d",
            "share_gaps_le_3d",
            "share_gaps_le_7d",
            "cv_gap_dias",
            "burstiness_gap"
        ]),
        on="NUM_CPF",
        how="left"
    )

    # BLOCO E — intensidade e extremos
    .join(
        perfil_intensidade_cpf.select([
            "NUM_CPF",
            "evt_max_dia",
            "evt_mean_dia",
            "dias_ativos",
            "ratio_pico_media",
            "share_pico_total",
            "flag_super_pico"
        ]),
        on="NUM_CPF",
        how="left"
    )
)

print(f"[OK] BLOCO F — INTEGRAÇÃO FINAL concluída em {time.time()-t0:.2f}s")

#################################################################################
#primeira exportação (saltar - quebrou o modelo do Dayan na leitura)

#variaveis criadas
assert perfil_final_df.select("NUM_CPF").n_unique() == perfil_final_df.height

output_path = r"C:\Users\cezar\Downloads\hackathon\nossasProducoes\recarga_bureau_features.parquet"
perfil_final_df.write_parquet(
    output_path,
    compression="snappy",
    statistics=True
)
print(f"[OK] Parquet único gerado em: {output_path}")
print(perfil_final_df.shape)

#base filtrada por BUREAU
###################################
# PARQUET 1 — EVENTOS ENRIQUECIDOS
###################################
t0 = time.time()

# 1) Garantia de tipos e LAZY explícito
eventos_base = (
    eventos_com_bureau
    .with_columns(pl.col("NUM_CPF").cast(pl.Utf8))
    .lazy()
)

perfil_features = (
    perfil_final_df
    .with_columns(pl.col("NUM_CPF").cast(pl.Utf8))
    .lazy()
)

# 2) Join EVENTO × PERFIL CPF (LAZY x LAZY)
eventos_enriquecidos = (
    eventos_base
    .join(
        perfil_features,
        on="NUM_CPF",
        how="left"
    )
)

# 3) Checks de sanidade (materialização controlada)
checks_eventos = (
    eventos_enriquecidos
    .select(
        pl.len().alias("linhas_total"),
        pl.col("NUM_CPF").n_unique().alias("cpfs_unicos")
    )
    .collect()
)

print("[CHECKS — EVENTOS ENRIQUECIDOS]")
print(checks_eventos)

# 4) Escrita do parquet (STREAMING, SEM COLLECT)
output_path = "eventos_recarga_bureau_enriquecidos.parquet"

eventos_enriquecidos.sink_parquet(
    output_path,
    compression="zstd",
    statistics=True
)

print(f"[OK] PARQUET SALVO EM: {output_path}")
print(f"[TEMPO] {time.time()-t0:.2f}s")

#exporta dimensao útil
t0 = time.time()
base_dir = r"C:\Users\cezar\Downloads\hackathon\bases_recarga"

csv_path = os.path.join(base_dir, "BI_DIM_INSTITUICAO.csv")
output_path = os.path.join(base_dir, "dim_instituicao.parquet")

# 1) Leitura da dimensão
dim_instituicao = pl.read_csv(
    csv_path,
    infer_schema_length=10000
)

# 2) Checagem mínima de colunas críticas
cols_obrigatorias = ["DW_INSTITUICAO", "COD_TIPO_INSTITUICAO"]
missing = [c for c in cols_obrigatorias if c not in dim_instituicao.columns]
if missing:
    raise ValueError(f"Colunas obrigatórias ausentes: {missing}")

# 3) Padronização + garantia de PK
dim_instituicao = (
    dim_instituicao
    .with_columns([
        pl.col("DW_INSTITUICAO").cast(pl.Int64),
        pl.col("COD_TIPO_INSTITUICAO").cast(pl.Int32)
    ])
    .unique(subset=["DW_INSTITUICAO"])
)

# 4) Checks rápidos
checks_dim = dim_instituicao.select(
    pl.len().alias("qtd_instituicoes"),
    pl.col("COD_TIPO_INSTITUICAO").n_unique().alias("tipos_instituicao_distintos")
)

print("\n[CHECKS — DIM_INSTITUICAO]")
print(checks_dim)

# 5) Escrita do parquet
dim_instituicao.write_parquet(
    output_path,
    compression="zstd",
    statistics=True
)

print(f"\n[OK] PARQUET 3 (DIM_INSTITUICAO) SALVO EM:")
print(output_path)
print(f"[TEMPO] {time.time() - t0:.2f}s")


##################################################################################
# Exportação com conversão de tipos e divisão em múltiplos Parquets
# substitui UInts (8, 16, 32...) por Int e Float 64
def normalize_numeric_types(df: pl.DataFrame) -> pl.DataFrame:
    exprs = []
    for c, dt in zip(df.columns, df.dtypes):
        if dt in (pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64, pl.Int8, pl.Int16, pl.Int32):
            exprs.append(pl.col(c).cast(pl.Int64))
        elif dt == pl.Float32:
            exprs.append(pl.col(c).cast(pl.Float64))
        else:
            exprs.append(pl.col(c))
    return df.select(exprs)


###################################
# CONFIGURAÇÕES
###################################
base_out = r"C:\Users\cezar\Downloads\hackathon\nossasProducoes"
os.makedirs(base_out, exist_ok=True)

UINT_TYPES = {pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64}
SMALL_INT_TYPES = {pl.Int8, pl.Int16, pl.Int32}

###################################
# PARQUET 2 — FEATURES POR CPF (SPLIT EM 5)
###################################
t0 = time.time()

# 1) Garantia de unicidade (LAZY-safe)
checks_unicidade = (
    perfil_cpf
    .select([
        pl.len().alias("linhas"),
        pl.col("NUM_CPF").n_unique().alias("cpfs_unicos"),
    ])
    .collect()
)
assert checks_unicidade["linhas"][0] == checks_unicidade["cpfs_unicos"][0]

# 2) Correção explícita de tipos (ainda LAZY)
exprs_features = []

schema_perfil = perfil_cpf.collect_schema()

for col, dtype in schema_perfil.items():
    if col == "NUM_CPF":
        exprs_features.append(pl.col(col).cast(pl.Utf8))
    elif dtype in UINT_TYPES or dtype in SMALL_INT_TYPES:
        exprs_features.append(pl.col(col).cast(pl.Int64))
    elif dtype == pl.Float32:
        exprs_features.append(pl.col(col).cast(pl.Float64))
    else:
        exprs_features.append(pl.col(col))

perfil_features_lazy = perfil_cpf.select(exprs_features)

# >>> MATERIALIZAÇÃO ÚNICA (OBRIGATÓRIA PARA SPLIT) <<<
perfil_features_df = perfil_features_lazy.collect()

# 3) Split correto em 5 arquivos (EAGER)
n_parts = 1
perfil_features_split = (
    perfil_features_df
    .with_row_count("_row_nr")
    .with_columns((pl.col("_row_nr") % n_parts).alias("_part"))
)

for i, part in enumerate(
    perfil_features_split.partition_by("_part", as_dict=False)
):
    out_path = os.path.join(
        base_out,
        f"recarga_bureau_features_part{i+1}_semUInt.parquet"
    )

    part.drop(["_row_nr", "_part"]).write_parquet(
        out_path,
        compression="snappy",
        statistics=True
    )

print("[OK] PARQUET 2 (FEATURES) GERADO EM 1 PARTE(S)")
print(f"[TEMPO] {time.time()-t0:.2f}s")


###################################
# PARQUET 1 — EVENTOS ENRIQUECIDOS (STREAMING)
###################################
t0 = time.time()

eventos_base = (
    eventos_com_bureau
    .with_columns(pl.col("NUM_CPF").cast(pl.Utf8))
    .lazy()
)

perfil_features_lazy = perfil_features_safe.lazy()

eventos_enriquecidos = (
    eventos_base
    .join(perfil_features_lazy, on="NUM_CPF", how="left")
)

schema_evt = eventos_enriquecidos.collect_schema()

exprs_evt = []
for col, dtype in schema_evt.items():
    if dtype in UINT_TYPES or dtype in SMALL_INT_TYPES:
        exprs_evt.append(pl.col(col).cast(pl.Int64).alias(col))
    elif dtype == pl.Float32:
        exprs_evt.append(pl.col(col).cast(pl.Float64).alias(col))
    else:
        exprs_evt.append(pl.col(col))

eventos_enriquecidos_safe = eventos_enriquecidos.select(exprs_evt)

checks_eventos = (
    eventos_enriquecidos_safe
    .select(
        pl.len().alias("linhas_total"),
        pl.col("NUM_CPF").n_unique().alias("cpfs_unicos")
    )
    .collect()
)

print("[CHECKS — EVENTOS ENRIQUECIDOS]")
print(checks_eventos)

out_evt = os.path.join(
    base_out,
    "eventos_recarga_bureau_enriquecidos_semUInt.parquet"
)

eventos_enriquecidos_safe.sink_parquet(
    out_evt,
    compression="zstd",
    statistics=True
)

print(f"[OK] PARQUET 1 SALVO EM: {out_evt}")
print(f"[TEMPO] {time.time()-t0:.2f}s")

###################################
# PARQUET 3 — DIM_INSTITUICAO
###################################
t0 = time.time()

base_dim = r"C:\Users\cezar\Downloads\hackathon\bases_recarga"
csv_dim = os.path.join(base_dim, "BI_DIM_INSTITUICAO.csv")
out_dim = os.path.join(base_out, "dim_instituicao_semUInt.parquet")

dim_instituicao = (
    pl.read_csv(csv_dim, infer_schema_length=10000)
    .with_columns([
        pl.col("DW_INSTITUICAO").cast(pl.Int64),
        pl.col("COD_TIPO_INSTITUICAO").cast(pl.Int32)
    ])
    .unique(subset=["DW_INSTITUICAO"])
)

checks_dim = dim_instituicao.select(
    pl.len().alias("qtd_instituicoes"),
    pl.col("COD_TIPO_INSTITUICAO").n_unique().alias(
        "tipos_instituicao_distintos"
    )
)

print("\n[CHECKS — DIM_INSTITUICAO]")
print(checks_dim)

dim_instituicao.write_parquet(
    out_dim,
    compression="zstd",
    statistics=True
)

print(f"[OK] PARQUET 3 SALVO EM: {out_dim}")
print(f"[TEMPO] {time.time()-t0:.2f}s")
