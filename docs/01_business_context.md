# Contexto de Negócio

---

##  Problema

Identificar clientes da base pré-pago com maior probabilidade de inadimplência, permitindo ações preventivas e otimização de políticas de crédito.

> **Risco de Crédito**: Chance de famílias e empresas NÃO cumprirem com suas obrigações, resultando em perdas.

---

##  Dimensão do Desafio

- **Base**: 50 milhões de assinantes pré-pagos
- **Taxa de aprovação atual**: 73-74%
- **Grupo controle**: ~2% (6º e 7º dígitos do CPF)
- **Período**: Out/2024 - Mar/2025

---

##  Objetivo Estratégico

**Cenário 1**: ↑ Aprovação mantendo inadimplência  
**Cenário 2**: ↓ Inadimplência mantendo aprovação  
**Ideal**: Ganho incremental em ambos via políticas hiper-segmentadas

---

##  Diferencial: Crédito Claro Score ≠ Crédito Tradicional

**Case Real**:
- Cliente pré-pago: Histórico consistente de recarga, sem histórico bancário
- Modelo tradicional: Alto risco → ❌ Negado
- Com dados de recarga: Reclassificado → ✅ Aprovado
- Resultado: Retenção + Receita (pós > pré)


---

##  Métricas de Sucesso

**Benchmark (Out-of-Time Fev/Mar)**:

| Métrica | Objetivo |
|---------|----------|
| **KS** | ≥ 33,1 |
| **GINI** | Máximo possível |
| **Taxa de Aprovação** | ~73-74% (baseline) |


**⚠️ Importante**: 
> Análise completa da curva ROC. **Foco na metade inferior** (maior impacto de negócio).

---

## Estratégia: Modelagem Incremental

Avaliar **ROI de cada fonte de dados**:

```
1. Baseline (CPF + Safra + Target)     → KS base
2. + Book Atraso/Pagamento             → Δ KS
3. + Book Recarga                      → Δ KS (Diferencial!)
4. + Dados Cadastrais                  → Δ KS
5. + Dados TELCO                       → Δ KS
6. + Scores Bureau Externos            → KS final
```

**Exemplo de ganho real**: Book Atraso/Pagamento (KS 15) + Book Recarga = KS 25 (**+10 pontos**)

**Justificativa**: Viabilizar investimento em dados externos baseado em ganho incremental.

---

## Metodologia: Books de Variáveis

**Conceito**: Estruturas pré-calculadas de variáveis categorizadas por assunto.

**Benefícios**:
-  Padronização e reutilização
-  Eficiência computacional
-  Governança de dados

**Books utilizados**:
- `book_atraso`: Padrões de atraso
- `book_pagamento`: Histórico transacional
...

---

##  Validação

**Safras de Modelagem**:
- **Treino**: Safras 1-4 (4 meses)
- **Validação Out-of-Time**: Fev/Mar (obrigatório)

**Grupo Controle**:
- Todos aprovados (exceto óbitos e menores)
- Permite comparação direta da política

---

##  Impacto Esperado

-  Captura de oportunidades (migração pré → pós)
-  Redução de perdas por inadimplência
-  Políticas de crédito hiper-segmentadas
-  Decisões preventivas baseadas em dados

---

*Super Hackathon 2025 | Patrocinadora: Claro*
