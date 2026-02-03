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
- 🔄 Desenvolver modelo behavior reprodutível e escalável (em andamento)
- 🔄 Gerar insights acionáveis para estratégias de mitigação de risco (em andamento)

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
| **KS** | ≥ 33,1 (benchmark) | 🔄 Em avaliação |
| **GINI** | Máximo possível | 🔄 Em avaliação |
| **Taxa de Aprovação** | ~73-74% (baseline) | 🔄 Em avaliação |
| **Taxa de Inadimplência** | ≤ Baseline grupo controle | 🔄 Em avaliação |

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

**Para mais detalhes**: Consulte [docs/08_architecture.md](docs/08_architecture.md) *(em desenvolvimento)*

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
- **XGBoost / LightGBM** - Algoritmos de boosting *(planejado)*
- **Jupyter Notebooks** - Experimentação e análise

### Visualização
- **Power BI** - Dashboards corporativos
- **AWS QuickSight** - Visualizações em nuvem
- **Matplotlib / Seaborn** - Visualizações Python

---

## 📊 Bases de Dados

### Bases Disponibilizadas pela Claro

| Base | Descrição | Granularidade | Volume Estimado | Responsável EDA |
|------|-----------|---------------|-----------------|-----------------|
| `base_dados_cadastrais` | Informações cadastrais dos clientes | CPF | ~10M registros | [Nome] |
| `base_score_bureau_movel` | Score de crédito bureau | CPF + Data | ~15M registros | [Nome] |
| `base_score_bureau_movel_full` | Score com flag 0 para clientes reprovados | CPF + Data | ~20M registros | [Nome] |
| `base_telco` | Dados de uso e serviços telco | CPF + Mês | ~50M registros | [Nome] |
| `book_atraso` | Histórico de atrasos | CPF + Evento | ~5M registros | [Nome] |
| `book_pagamento` | Histórico de pagamentos | CPF + Transação | ~80M registros | [Nome] |

### Books de Variáveis

**Conceito**: Estruturas pré-calculadas de variáveis categorizadas por assunto, desenvolvidas para:
- ✅ Padronização e reutilização
- ✅ Eficiência computacional
- ✅ Governança de dados

**Books Utilizados**:
- `book_atraso` - Variáveis de comportamento de atraso
- `book_pagamento` - Variáveis de histórico transacional


**Dicionários completos**: Disponíveis em [docs/data_dictionary/](docs/data_dictionary/)

---

## 📂 Estrutura do Projeto

```
modelo-behavior-claro/
│
├── README.md                          # Este arquivo
├── diagrama_arquitetura.jpg          # Diagrama da arquitetura AWS
│
├── docs/                              # Documentação detalhada
│   ├── 01_business_context.md        # Contexto de negócio completo
│   ├── 02_data_understanding.md      # Entendimento das bases de dados
│   ├── 03_eda_insights.md            # Resumo dos insights das EDAs (em desenvolvimento)
│   │
│   ├── data_dictionary/              # Dicionários de dados de cada base
│   │   ├── base_cadastrais.xlsx
│   │   ├── base_recarga.xlsx
│   │   ├── base_telco.xlsx
│   │   └── ... (um por base)
│   │
│   ├── book_variaveis/               # Books de variáveis
│   │   ├── book_atraso.xlsx
│   │   ├── book_pagamento.xlsx
│   
│
├── notebooks/                         # Análises exploratórias (EDAs)
│   ├── eda_cadastrais.ipynb          # EDA - Base cadastral
│   ├── eda_recarga.ipynb             # EDA - Base recarga
│   ├── eda_telco.ipynb               # EDA - Base telco
│   ├── eda_score_bureau.ipynb        # EDA - Score bureau
│   ├── eda_atraso.ipynb              # EDA - Book atraso
│   └── eda_pagamento.ipynb           # EDA - Book pagamento
│
└── models/                            # Modelos (em desenvolvimento)
    └── baseline/                      # Modelo baseline
```

---

## 🔄 Trabalho em Progresso

> ⚠️ Este projeto está em desenvolvimento ativo. As seções abaixo serão atualizadas conforme o projeto evolui.

### Pipeline de Dados

**Status**: 🔄 Em desenvolvimento

**Progresso**:
- [x] Ingestão de dados (Bronze layer)
- [x] Catalogação com Glue
- [ ] Transformação Bronze → Silver
- [ ] Agregação Silver → Gold (visão única por CPF)
- [ ] Feature engineering
- [ ] Validação de qualidade de dados

**Documentação**: Será disponibilizada em `docs/04_data_preparation.md` após implementação.

---

### Feature Engineering

**Status**: 🔄 Em desenvolvimento

**Abordagem Planejada**:
- Agregações temporais (3, 6, 12 meses)
- Features comportamentais de recarga
- Features financeiras de crédito
- Ratios e tendências

**Documentação**: Será disponibilizada em `docs/05_feature_engineering.md` conforme evolução.

---

### Modelagem

**Status**: 🔄 Iniciado (em andamento)

**Estratégia**:
- Modelagem incremental (conforme orientação Claro)
- Avaliação de ganho por fonte de dados
- Validação out-of-time (safras fev/mar)
- Benchmark: KS ≥ 33,1

**Progresso Atual**:
- [x] Definição de estratégia
- [x] Análise exploratória das bases
- [ ] Integração de dados (visão única por CPF)
- [ ] Feature engineering
- [ ] Treinamento modelo baseline
- [ ] Modelagem incremental (6 versões)
- [ ] Otimização de hiperparâmetros
- [ ] Validação final

**Documentação**: Será disponibilizada em `docs/06_modeling.md` conforme modelo evolui.

---

### Como Reproduzir

**Status**: ⏳ Aguardando finalização do pipeline

O processo completo de reprodução será documentado após a implementação e integração de todos os componentes.

**Atualmente disponível**:
- Notebooks individuais de EDA (em `notebooks/`)
- Dicionários de dados (em `docs/data_dictionary/`)
- Books de variáveis (em `docs/book_variaveis/`)

**Em breve**:
- Scripts de ingestão de dados
- Pipeline de transformação
- Scripts de feature engineering
- Scripts de treinamento de modelos

---

### Resultados

**Status**: ⏳ Aguardando conclusão da modelagem

As métricas e resultados serão atualizados assim que o modelo baseline estiver treinado e validado.

**Métricas que serão reportadas**:
- KS Statistic (objetivo: ≥ 33,1)
- GINI Coefficient
- Curva ROC / AUC
- Taxa de Aprovação vs Inadimplência
- Feature Importance
- Análise de Swap In / Swap Out

---

## 👥 Time

### Super Hackathon 2025 - Equipe Behavior Claro

**Líder**: Rafael Lima

**Membros**:
- Daniel Dayan
- Diego Lessa
- Gabriel Lenhard
- Gabriel Roledo
- Tiago Carvalho
- Cézar Augusto Freitas
- Grazy Miranda
- Ricardo Max

### Divisão de Responsabilidades

- **Análises Exploratórias (EDAs)**: Cada membro responsável por uma base de dados
- **Feature Engineering**: Desenvolvimento colaborativo de variáveis preditivas
- **Modelagem**: Desenvolvimento e otimização do modelo baseline
- **Infraestrutura AWS**: Implementação da arquitetura Medallion
- **Documentação**: Consolidação de informações e reprodutibilidade

---

## 📚 Documentação Detalhada

A documentação completa do projeto está organizada na pasta `docs/`:

### Disponível Agora ✅

- **[Contexto de Negócio](docs/01_business_context.md)**: Problema, objetivos, case de sucesso, métricas
- **[Entendimento dos Dados](docs/02_data_understanding.md)**: Descrição das bases, dicionários, books

### Em Desenvolvimento 🔄

- **EDA e Insights**: Resumo das análises exploratórias (em compilação)
- **Data Preparation**: Limpeza, validação, grupo controle (aguardando implementação)
- **Feature Engineering**: Criação de variáveis preditivas (em andamento)
- **Modelagem**: Processo incremental completo (em andamento)
- **Avaliação**: Métricas, validação out-of-time (aguardando resultados)
- **Arquitetura**: Detalhamento técnico Medallion (em elaboração)

### Recursos Adicionais

- **[Dicionários de Dados](docs/data_dictionary/)**: Excel com metadados de cada base
- **[Books de Variáveis](docs/book_variaveis/)**: Estruturas pré-calculadas da Claro

---

## 🙏 Agradecimentos

- **Claro** pela disponibilização dos dados reais e patrocínio do desafio
- **Fábio Oliveira** (Claro - Crédito e Cobrança) pelas orientações técnicas detalhadas
- **PoD Academy** pela organização do Super Hackathon 2025
- Todos os membros do time pela dedicação e colaboração

---

## 📌 Roadmap

- [x] Definição do problema e objetivos ✅
- [x] Estruturação do projeto ✅
- [x] Setup de infraestrutura AWS ✅
- [x] Análise exploratória das bases 🔄
- [ ] Integração de dados (visão única por CPF) 🔄
- [ ] Feature engineering 🔄
- [ ] Modelo baseline 🔄
- [ ] Modelagem incremental (6 versões) ⏳
- [ ] Validação out-of-time ⏳
- [ ] Otimização de hiperparâmetros ⏳
- [ ] Análise de resultados ⏳
- [ ] Documentação completa ⏳
- [ ] Apresentação final ⏳

**Legenda**: ✅ Concluído | 🔄 Em Andamento | ⏳ Aguardando

---

## 📞 Contato

**Super Hackathon 2025**  
**Patrocinadora**: Claro  
**Time**: Behavior Claro  
**Líder**: Rafael Lima

---

<div align="center">

**Desenvolvido com ❤️ pela Equipe Behavior Claro**

Super Hackathon 2025

*"Transformando dados em oportunidades de negócio através de gestão inteligente de risco"*

</div>
