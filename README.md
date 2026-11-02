# 🔍 Catálogo Inteligente com Elasticsearch & Streamlit

Aplicação prática e totalmente dockerizada demonstrando os recursos essenciais do **Elasticsearch 8** integrados a um frontend interativo em **Streamlit**.

## ✨ O que esta aplicação demonstra na prática?

1. **Index Mapping explícito** (`text`, `keyword`, `float`, `boolean`, `date`) e ingestão em lote com `helpers.bulk`.
2. **Full-Text Search (`multi_match`)** com pesos por campo (`title^3`, `tags^2`, `brand^2`, `description`).
3. **Fuzzy Search (`fuzziness: AUTO`)** tolerante a erros de digitação (ex: pesquise por `notebok` ou `samsumg`).
4. **Highlighting** destacando em amarelo os termos encontrados no título e na descrição.
5. **Query Booleana (`bool`)** combinando relevância (`must` + score BM25) com filtros exatos em cache (`filter` com `terms`, `range` e `term`).
6. **Aggregations em tempo real** (`terms`, `stats` e `range`) que geram gráficos e estatísticas dinâmicas conforme você filtra.
7. **CRUD direto pelo painel** (indexar novos produtos, excluir por ID ou resetar o índice) e **Inspeção da Query DSL JSON** gerada em tempo real.

## 🚀 Como executar

Suba os containers com Docker Compose:

```bash
docker compose up --build -d
```

- **Frontend (Streamlit):** http://localhost:8501
- **API do Elasticsearch:** http://localhost:9200

Para encerrar e remover os volumes:

```bash
docker compose down -v
```

