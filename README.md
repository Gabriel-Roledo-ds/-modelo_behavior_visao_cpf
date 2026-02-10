# 🎯 Modelo Behavior Claro - Predição de Risco de Crédito

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![AWS](https://img.shields.io/badge/AWS-Cloud-orange.svg)](https://aws.amazon.com/)
[![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow.svg)]()
[![Hackathon](https://img.shields.io/badge/Super%20Hackathon-2025-orange.svg)]()

> Modelo de predição de risco de inadimplência para clientes pré-pagos da Claro baseado em visão única por CPF

---

## 📑 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Problema de Negócio](#-problema-de-negócio)
- [Arquitetura da Solução](#-arquitetura-da-solução)
- [Stack Tecnológico](#-stack-tecnológico)
- [Bases de Dados](#-bases-de-dados)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Trabalho em Progresso](#-trabalho-em-progresso)
- [Time](#-time)
- [Documentação Detalhada](#-documentação-detalhada)

---

## 🎯 Sobre o Projeto

Este projeto está sendo desenvolvido durante o **Super Hackathon 2025** com o objetivo de criar um modelo preditivo de risco de crédito para identificar clientes da base pré-pago da Claro com maior probabilidade de se tornarem inadimplentes.

### Objetivos Principais

- ✅ Construir visão única de cliente por CPF consolidando múltiplas bases
- ✅ Identificar padrões comportamentais de inadimplência
- ✅ Desenvolver modelo behavior baseline reprodutível e escalável
- ✅ Gerar insights acionáveis para estratégias de mitigação de risco 

---

## 💼 Problema de Negócio

### Desafio

Identificar, entre os clientes da base pré-pago, quais têm maior probabilidade de se tornarem inadimplentes, permitindo ações preventivas e estratégias de mitigação de risco.


### Contexto Estratégico da Claro

**Dimensão do Desafio**:
- 🎯 **50 milhões de assinantes** na base
- 📊 **Taxa de aprovação atual**: 73-74%
- 🎲 **Grupo controle**: ~2% da base (seleção por 6º e 7º dígitos do CPF)
- 🔄 **Análise contínua** influenciada por fatores de mercado, regulação e economia

**Objetivo Estratégico**:
- **Cenário 1**: Aumentar taxa de aprovação **mantendo** inadimplência estável
- **Cenário 2**: Reduzir inadimplência **mantendo** taxa de aprovação estável
- **Ideal**: Ganho incremental em ambas as dimensões através de políticas hiper-segmentadas

### Case de Sucesso Real

**Situação**: Cliente pré-pago com histórico consistente de recarga, mas sem histórico bancário robusto

**Problema**: Modelo tradicional classificaria como **alto risco** → Cliente negado para pós-pago

**Solução**: Análise de padrão de recarga permite reclassificação de Alto → Médio/Baixo risco

**Resultado**: ✅ Cliente aprovado, ✅ Retenção, ✅ Aumento de receita (pós > pré)


### Métricas de Sucesso

**Benchmark Estabelecido (Out-of-Time Fev/Mar)**:

| Métrica | Objetivo | Status |
|---------|----------|---------|
| **KS** | ≥ 33,1 (benchmark) | 🔄 Em desenvolvimento (Baseline 30)|
| **GINI e Curva ROC** | Máximo possível | 🔄 Em desenvolvimento (Baseline Curva ROC 0,703 | GINI 0,407) |
| **Taxa de Aprovação** | ~73-74% (baseline) | 🔄 Em desenvolvento |
| **Taxa de Inadimplência** | ≤ Baseline grupo controle | 🔄 Em desenvolvimento |

> A análise considera toda a curva ROC e matriz de confusão, com **foco especial na metade inferior da curva de score** (onde está o maior impacto de negócio).

### Estratégia de Modelagem Incremental

A abordagem de **modelagem incremental** avalia viabilidade econômica de cada fonte de dados:

```
1. Baseline (CPF + Safra + Target)           → KS base
2. + Book Atraso/Pagamento                   → Medir ganho ΔKS
3. + Book Recarga                            → Medir ganho ΔKS
4. + Dados Cadastrais                        → Medir ganho ΔKS
5. + Dados TELCO                             → Medir ganho ΔKS
6. + Scores Bureau Externos                  → KS final
```

**Justificativa**: Viabilizar decisões de investimento em aquisição de dados externos baseadas em ROI de cada fonte.

**Para mais detalhes**: Consulte [docs/01_business_context.md](docs/01_business_context.md)

---

## 🏗️ Arquitetura da Solução

![Arquitetura AWS](diagrama_arquitetura.jpg)

### Visão Geral

A solução utiliza arquitetura **Medallion** (Bronze → Silver → Gold) na AWS, garantindo qualidade, governança e escalabilidade dos dados.

**Camadas**:
- **Bronze**: Dados brutos ingeridos de fontes externas (Oracle, PostgreSQL, APIs)
- **Silver**: Dados limpos e validados após transformações
- **Gold**: Dados agregados e prontos para consumo (visão única por CPF + features)

**Componentes Principais**:
- **AWS S3**: Data Lake (armazenamento em todas as camadas)
- **AWS Lambda**: Processamento serverless de ingestão e transformações leves
- **AWS Glue**: Catalogação de dados e descoberta de esquemas
- **Amazon EMR**: Processamento distribuído com PySpark para transformações pesadas
- **Amazon SageMaker**: Treinamento e deployment de modelos de ML
- **Amazon Redshift**: Data Warehouse para analytics
- **Amazon Athena**: Queries SQL serverless
- **Power BI**: Dashboards e visualizações



---

## 🛠️ Stack Tecnológico

### Processamento e Análise
- **Python 3.8+** - Linguagem principal
- **Pandas** - Análise e manipulação de dados
- **Polars** - Processamento de alta performance
- **PySpark** - Processamento distribuído
- **SQL** - Queries e transformações

### Cloud e Infraestrutura (AWS)
- **S3** - Data Lake (Bronze/Silver/Gold)
- **Lambda** - Processamento serverless
- **Glue** - Catalogação e ETL
- **EMR** - Cluster Spark
- **SageMaker** - ML training e deployment
- **Redshift** - Data Warehouse
- **Athena** - Queries SQL
- **IAM** - Controle de acesso
- **KMS** - Criptografia
- **CloudWatch** - Monitoramento

### Machine Learning
- **Scikit-learn** - Modelagem e avaliação
- **XGBoost / LightGBM/CatBoost/GradientBoost/RandomForest** - Algoritmos de bagging e boosting *(planejado)*
- **Regressão Logística/ Arvore de decisão** - Algoritmos Nativos
- **Jupyter Notebooks** - Experimentação e análise
  

### Visualização
- **Power BI** - Dashboards corporativos
- **AWS QuickSight** - Visualizações em nuvem
- **Matplotlib / Seaborn** - Visualizações Python
- **Excell** 

---

## 📊 Bases de Dados

### Bases Disponibilizadas pela Claro

| Base | Descrição | Granularidade | Volume Estimado | Responsável EDA |
|------|-----------|---------------|-----------------|-----------------|
| `base_dados_cadastrais` | Informações cadastrais dos clientes | CPF | ~10M registros | Gabriel Roledo |
| `base_score_bureau_movel` | Score de crédito bureau | CPF + Data | ~15M registros | Daniel Dayan |
| `base_telco` | Dados de uso e serviços telco | CPF + Mês | ~50M registros | Gabriel Lenhart & Daniel Dayan |
| `book_atraso` | Histórico de atrasos | CPF + Evento | ~5M registros | Daniel Dayan|
| `book_pagamento` | Histórico de pagamentos | CPF + Transação | ~80M registros | Daniel Dayan |
| 'base_recarga' | Histórico de recargas  | CPF + data | ~100 registros | Cézar Augusto

### Books de Variáveis

**Conceito**: Estruturas pré-calculadas de variáveis categorizadas por assunto, desenvolvidas para:
- ✅ Padronização e reutilização
- ✅ Aumento de poder preditivo
- ✅ Captura de comportamentos e tendências temporais

**Books Utilizados**:
- `book_atraso` - Variáveis de comportamento de atraso
- `book_pagamento` - Variáveis de histórico transacional
- 'book_recarga' - Variáveis de histórico de recarga


**Dicionários completos**: Disponíveis em [docs/data_dictionary/](docs/data_dictionary/)




---

### Feature Engineering


**Abordagem Planejada**:
- Agregações temporais (1, 3, 6, 9, 12 meses)
- Features comportamentais de recarga/pagamento/atraso
- Ratios e tendências



---

### Modelagem


**Estratégia**:
- Modelagem incremental (conforme orientação Claro)
- Avaliação de ganho por fonte de dados
- Validação out-of-time (safras fev/mar)
- Benchmark: KS ≥ 33,1


---



## 👥 Time

### Super Hackathon 2025 - Equipe Behavior Claro

**Líder**: Rafael Lima

**Membros**:
- Daniel Dayan
- Gabriel Lenhart
- Gabriel Roledo
- Cézar Augusto Freitas
- Ricardo Max

### Divisão de Responsabilidades

- **Análises Exploratórias (EDAs)**: Daniel Dayan, Cézar Augusto Freitas, Gabriel Lenhart e Gabriel Roledo
- **Feature Engineering**: Daniel Dayan e Cézar Augusto Freitas
- **Modelagem**: Daniel Dayan
- **Engenharia de dados**: Ricardo Max
- **Documentação**: Gabriel Roledo
---

## 📚 Documentação Detalhada

A documentação completa do projeto está organizada na pasta `docs/`:

### Disponível Agora ✅

- **[Contexto de Negócio](docs/01_business_context.md)**: Problema, objetivos, case de sucesso, métricas
- **[Insights das EDA](docs/02_eda_insights.md)**: Resumo dos insights



### Recursos Adicionais

- **[Dicionários de Dados](docs/data_dictionary/)**: Excel com metadados de cada base
- **[Books de Variáveis](docs/book_variaveis/)**: Estruturas pré-calculadas da Claro

---

## 🙏 Agradecimentos

- **Claro** pela disponibilização dos dados reais, orientações técnicas detalhadas e patrocínio do desafio
- **Toda a Equipe PoD Academy** pela organização e suporte aos participantes do Super Hackathon 2025
- Todos os membros do time pela dedicação e colaboração

---








<div align="center">

**Squad 9**
**Super Hackaton 2026**



</div>
