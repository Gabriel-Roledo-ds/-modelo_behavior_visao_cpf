# Insights das Análises Exploratórias

---

## 📊 Base: Dados Cadastrais

**Responsável**: Gabriel Roledo | **Registros**: 3.900.378 | **Variáveis**: 33  
**Notebook**: [eda_cadastrais.ipynb](../notebooks/eda_cadastrais.ipynb) | **Dicionário**: [dicionario_cadastrais.docx](data_dictionary/dicionario_cadastrais.docx)

---

### Visão Geral

A análise foi conduzida a partir de um merge, considerando as variáveis ID (CPF + safra) e FPD_SCORE presentes no FPD da base Bureau. O período analisado compreende out/2024 a mar/2025, totalizando 6 safras.

---

### Qualidade dos Dados

- **CPFs únicos**: 1.272.095 (pós-join)
- **Duplicados**: 18.431 CPFs em múltiplas safras (mesmo cliente, meses diferentes)
- **Nulos críticos**: var_17 (100%), var_02/10/11/14/20/22 (>80%)
- **Padrão**: Ausência de dados correlaciona com maior FPD

---

### Variáveis Destaque

**1. var_08 (Score 0-100)** 
Clara separação FPD=0 vs FPD=1. FPD=1 concentra em valores altos (80-90).

![var_08 vs FPD](figures/cadastrais_kde_var08_fpd.png)

**2. Idade** 
Jovens (18-35): maior risco. Estabiliza após 45 anos. Anomalia aos 60 (aposentados?).  
Média: 42,4 anos

![Distribuição Idade](figures/cadastrais_distribuicao_idade.png)


**3. var_15 (UF)**   
MA/CE/RR: ~36% FPD | DF: ~26% FPD | **Δ 10pp regional**

MA, CE e RR aparecem com as maiores proporções de FPD, bem acima da linha de referência (média geral).
Já DF e GO estão entre os menores níveis de FPD, sugerindo performance significativamente melhor do que a média no período analisado.

![FPD por UF](figures/cadastrais_uf_fpd.png)

---

### Outliers Críticos

**var_07**: A "caixa" está totalmente esmagada no zero, com uma linha de outliers que se estende até 30 milhões.
Pode ser uma variável financeira (como renda ou limite) com pouquíssimos valores astronômicos que distorcem a média.
**var_11**: Densa nuvem de outliers

![Boxplot var11](figures/cadastrais_boxplot_var11.png)


### Perfil Etário no Momento da Proposta

Pico de solicitações: 35-45 anos (~70k por faixa). Anomalia aos 60 anos.

![Idade Proposta](figures/cadastrais_idade_proposta.png)

---

### Taxa de inadimplência por safra

Volatilidade Controlada:

A taxa de FPD flutua entre 22,3% e 24,9%.
Embora haja variação, ela ocorre dentro de um intervalo de aproximadamente 2,6 pontos percentuais, indicando uma carteira relativamente estável.

![Inadimplência por Safra](figures/cadastrais_fpd_safra.png)

### Anomalias

- **DATADENASCIMENTO**: Min=1900 (default), Max=2015 (menores?)
- **Multicolinearidade**: FLAG_INSTALACAO, PROD, flag_mig2, STATUSRF (correlação ~1.0)

---

### Recomendações

**Remover**: var_17 (100% nulos), FLAG_INSTALACAO, var_06 (constantes)  
**Tratar nulos**: var_04/05 criar categoria "-1"  
**Outliers**: var_07/11/16 log transform ou capping  
**Validação**: Out-of-time obrigatório (safras sequenciais)

---

---

## 📊 Base: Score Bureau Móvel

**Responsável**: Daniel Dayan | **Registros**: 1.290.526 | **Variáveis**: 8
**Notebook**: [eda_bureau_score.ipynb](../notebooks/eda_bureau_score.ipynb) | **Dicionário**: [dicionario_bureau.docx](data_dictionary/dicionario_bureau.docx)

---

### Visão Geral

Base de scores de crédito de bureaus externos. Granularidade: CPF + SAFRA. Target FPD 24% inadimplentes. Período: Out/2024-Mar/2025 (6 safras).

---

### Qualidade dos Dados

- **CPFs únicos**: 1.272.095
- **Duplicados**: 36.379 CPFs em múltiplas safras (mesmo cliente, safras diferentes)
- **Missing values**: ~0,7% em SCORE_01 e 0.04% em SCORE_02
- **Valores suspeitos**: Os valores 0, 1 e 2 aparecem no limite inferior do boxplot, indicando que além dos missing values, esss valores devem ser desconsiderados

---

### Descoberta Principal: Scores com Baixo Poder Preditivo ⚠️

**SCORE_01 e SCORE_02**: Ambos mostram **baixa capacidade discriminatória**

![Distribuição Scores vs FPD](figures/kde_score1_2_fpd.png)

**Observações:**
- Distribuições FPD=0 vs FPD=1 são muito sobrepostas
- Adimplentes têm score ligeiramente maior (esperado)
- Mas diferença é pequena demais para ser preditiva forte
- **Não são variáveis-chave** para o modelo

---

### Variáveis Comportamentais

**Score muda entre safras:**
- Análise de CPFs recorrentes mostra variação nos scores
- Scores capturam **comportamento recente**
- **Recomendação**: Usar última safra para cada CPF

---

### Variáveis para Remover

**3 constantes (cardinalidade = 1):**
- FLAG_INSTALACAO
- PROD
- flag_mig2

**Motivo**: Sem variação = sem poder preditivo. Removê-las reduz processamento.

---

### Sazonalidade

**Taxa de FPD por safra**: Pouca variabilidade entre safras (estável ~24%)

---

### Recomendações

1. **Tratar valores 0,1,2 como missing** (não são scores válidos)
2. **Remover 3 variáveis constantes** antes da modelagem
3. **Usar última safra** para CPFs duplicados
4. **Não depender exclusivamente dos scores** - poder preditivo limitado
5. **Combinar com outras bases** (cadastrais, recarga, telco) para ganho incremental

---
---

## 📊 Base: Book Atraso

**Responsável**: Daniel Dayan | **Registros**: 31.611.316 (transacional) → 1.290.526 (pós-join)  
**Variáveis**: 50 | **Período histórico**: Out/2023 - Mar/2025 (18 meses)  
**Notebook**: [eda_atraso.ipynb](../notebooks/eda_atraso.ipynb) | **Dicionário**: [dicionario_atraso.docx](data_dictionary/dicionario_atraso.docx)

---

### Visão Geral

Base **transacional** de faturas em atraso. Após join com Bureau: 1.290.526 registros. **1 ano de histórico** antes da primeira safra de modelagem (Out/2024).

**Granularidade**: Transação de fatura em atraso (múltiplas linhas por CPF)

---

### Qualidade dos Dados

- **Base transacional**: CPFs aparecem **apenas quando têm fatura em atraso**
- **CPFs duplicados**: Esperado (base transacional)
- **Recorrência máxima**: Cliente aparece em até 18 safras consecutivas (atraso crônico)
- **Missings críticos**: DAT_EXPIRACAO_DW (100%), DAT_CANCELAMENTO_FAT (100%)

---

### Variável-Chave: DW_FAIXA_AGING_DIVIDA 

**Única variável numérica com poder preditivo relevante:**

- Adimplentes têm aging de dívida **menor**
- Inadimplentes têm aging de dívida **maior**
- **Aging** = tempo desde vencimento da fatura

![Aging vs FPD](figures/atraso_aging_fpd.png)

---

### Variáveis Categóricas com Risco Diferenciado

**Plataforma (cod_plataforma):**
- **Alto risco**: M2MS, POSTL, PREPG
- Classificação do perfil: Pós-Pago, Auto-Controle, Pré-pago

**Ponto de Venda:**
- 2 tipos específicos mostram risco maior (Claro já usa para modelagem)

**Observação**: Variabilidade de FPD existe, mas poucas categorias se destacam fortemente.

---

### Análise Temporal

**Histórico disponível**: Out/2023 - Mar/2025

**Padrão identificado:**
- ↑ Contagem de faturas em aberto ao longo do tempo
- ↑ Valor total em aberto aumenta por safra
- **Pico de pagamentos**: Setembro/2024
- **Picos de parcelamento**: Jun/24, Out/24, Dez/24

**Clientes recorrentes:**
- Máximo: 18 aparições (atraso em TODOS os meses)
- Mínimo: 1 aparição (atraso pontual)

---

### Comportamento da Base

**CPF só aparece quando há atraso:**
- Base **NÃO contém** clientes sem atraso
- É um filtro natural de risco
- Combinação com outras bases é essencial

**Estrutura transacional:**
- Múltiplas linhas por CPF
- ID_FATURA pode se repetir com NUM_ENT_SEQ_FATURA diferente
- Mesmo CONTRATO = mesmo DW_NUM_CLIENTE

---

### Outliers Financeiros

**Valores de fatura:**
- Outliers existem (~5% da base)
- São pagamentos reais de alto valor
- Não são erros de sistema

---

### Ideias de Features (Sugeridas na EDA)

**1. Frequência (1, 3, 6, 12 meses):**
- qtd_faturas_em_atraso
- qtd_meses_com_atraso
- taxa_meses_atraso

**2. Valor Financeiro:**
- val_total_em_atraso
- val_medio_fatura_atraso
- val_max_atraso

**3. Aging e Tempo:**
- dias_atraso_medio
- dias_atraso_maximo
- aging_medio_divida

**4. Reincidência:**
- teve_atraso_mes_anterior
- meses_consecutivos_atraso
- flag_atraso_cronico (>12 meses)

---

### Limitações

- **Poder preditivo geral**: Baixo para maioria das variáveis numéricas
- **Exceção**: DW_FAIXA_AGING_DIVIDA
- **Viés de seleção**: Base contém APENAS clientes com histórico de atraso
- **Necessário**: Combinar com bases de comportamento positivo (recarga, telco)

---

### Recomendações

1. **Criar features agregadas** (frequência, valor, aging) por período
2. **Usar histórico completo** (18 meses disponíveis)
3. **Identificar padrões de recorrência** (1 vez vs crônico)
4. **Combinar com outras bases** para balancear viés
5. **Atenção especial**: Plataformas M2MS, POSTL, PREPG

---

*Atualização: 07/02/2026*

