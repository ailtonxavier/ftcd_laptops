import os
import pandas as pd
import streamlit as st
from elasticsearch import Elasticsearch, helpers
from seed_data import load_laptops_from_csv

st.set_page_config(
    page_title="Laptops Explorer - Elasticsearch",
    page_icon="💻",
    layout="wide",
)

ES_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
INDEX_NAME = "laptops_catalog"


@st.cache_resource
def get_es_client() -> Elasticsearch:
    return Elasticsearch(ES_URL, request_timeout=15)


INDEX_SETTINGS = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
    },
    "mappings": {
        "properties": {
            "title": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "manufacturer": {"type": "keyword"},
            "model_name": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "category": {"type": "keyword"},
            "screen_size": {"type": "keyword"},
            "screen_inches": {"type": "float"},
            "screen": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "cpu": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "ram": {"type": "keyword"},
            "ram_gb": {"type": "integer"},
            "storage": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "gpu": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "os": {"type": "keyword"},
            "os_version": {"type": "keyword"},
            "weight": {"type": "keyword"},
            "weight_kg": {"type": "float"},
            "price_euros": {"type": "float"},
            "specs_summary": {"type": "text"},
        }
    },
}


def init_index(es: Elasticsearch, force_reset: bool = False) -> int:
    if force_reset and es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)

    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(index=INDEX_NAME, body=INDEX_SETTINGS)
        laptops = load_laptops_from_csv()
        actions = [
            {
                "_index": INDEX_NAME,
                "_id": str(i + 1),
                "_source": item,
            }
            for i, item in enumerate(laptops)
        ]
        helpers.bulk(es, actions, refresh=True)
        return len(laptops)
    return 0


def build_es_query(
    search_text: str,
    manufacturers: list[str],
    categories: list[str],
    ram_options: list[int],
    os_options: list[str],
    price_range: tuple[float, float],
    weight_range: tuple[float, float],
    fuzziness: bool,
    sort_option: str,
    page_size: int,
) -> dict:
    must_clauses = []
    filter_clauses = []

    if search_text.strip():
        multi_match = {
            "query": search_text.strip(),
            "fields": [
                "title^3",
                "model_name^2",
                "cpu^2",
                "gpu^2",
                "storage",
                "screen",
                "specs_summary",
            ],
            "operator": "or",
        }
        if fuzziness:
            multi_match["fuzziness"] = "AUTO"
        must_clauses.append({"multi_match": multi_match})
    else:
        must_clauses.append({"match_all": {}})

    if manufacturers:
        filter_clauses.append({"terms": {"manufacturer": manufacturers}})

    if categories:
        filter_clauses.append({"terms": {"category": categories}})

    if ram_options:
        filter_clauses.append({"terms": {"ram_gb": ram_options}})

    if os_options:
        filter_clauses.append({"terms": {"os": os_options}})

    filter_clauses.append(
        {"range": {"price_euros": {"gte": price_range[0], "lte": price_range[1]}}}
    )
    filter_clauses.append(
        {"range": {"weight_kg": {"gte": weight_range[0], "lte": weight_range[1]}}}
    )

    sort_map = {
        "Relevância (_score)": ["_score"],
        "Menor Preço (€)": [{"price_euros": "asc"}],
        "Maior Preço (€)": [{"price_euros": "desc"}],
        "Maior RAM (GB)": [{"ram_gb": "desc"}],
        "Mais Leve (kg)": [{"weight_kg": "asc"}],
    }

    return {
        "size": page_size,
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses,
            }
        },
        "sort": sort_map.get(sort_option, ["_score"]),
        "highlight": {
            "pre_tags": [
                "<mark style='background-color: #ffe066; color: #111; padding: 1px 4px; border-radius: 3px;'>"
            ],
            "post_tags": ["</mark>"],
            "fields": {
                "title": {},
                "specs_summary": {},
                "cpu": {},
                "gpu": {},
            },
        },
        "aggs": {
            "por_fabricante": {"terms": {"field": "manufacturer", "size": 20}},
            "por_categoria": {"terms": {"field": "category", "size": 10}},
            "por_ram": {"terms": {"field": "ram_gb", "size": 10}},
            "por_os": {"terms": {"field": "os", "size": 10}},
            "estatisticas_preco": {"stats": {"field": "price_euros"}},
            "estatisticas_peso": {"stats": {"field": "weight_kg"}},
            "faixas_preco": {
                "range": {
                    "field": "price_euros",
                    "ranges": [
                        {"key": "Até € 500", "to": 500},
                        {"key": "€ 500 - € 1.000", "from": 500, "to": 1000},
                        {"key": "€ 1.000 - € 1.500", "from": 1000, "to": 1500},
                        {"key": "€ 1.500 - € 2.500", "from": 1500, "to": 2500},
                        {"key": "Acima de € 2.500", "from": 2500},
                    ],
                }
            },
        },
    }


def get_initial_facets(es: Elasticsearch):
    res = es.search(
        index=INDEX_NAME,
        body={
            "size": 0,
            "aggs": {
                "manufacturers": {"terms": {"field": "manufacturer", "size": 50}},
                "categories": {"terms": {"field": "category", "size": 20}},
                "ram_gb": {
                    "terms": {
                        "field": "ram_gb",
                        "size": 20,
                        "order": {"_key": "asc"},
                    }
                },
                "os": {"terms": {"field": "os", "size": 20}},
                "max_price": {"max": {"field": "price_euros"}},
                "max_weight": {"max": {"field": "weight_kg"}},
            },
        },
    )
    aggs = res["aggregations"]
    manufacturers = [b["key"] for b in aggs["manufacturers"]["buckets"]]
    categories = [b["key"] for b in aggs["categories"]["buckets"]]
    ram_gb = [int(b["key"]) for b in aggs["ram_gb"]["buckets"]]
    os_list = [b["key"] for b in aggs["os"]["buckets"]]
    max_price = float(aggs["max_price"]["value"] or 6500.0)
    max_weight = float(aggs["max_weight"]["value"] or 5.0)
    return manufacturers, categories, ram_gb, os_list, max_price, max_weight


# --- UI Principal ---
st.title("💻 Catálogo de Laptops (`laptops.csv`) no Elasticsearch")
st.caption(
    "Base real com **1.303 laptops** indexada via **Bulk API** com **Full-Text Search (BM25)**, **Fuzzy Search**, **Highlighting**, **Bool Filters** e **Aggregations**."
)

es = get_es_client()

try:
    info = es.info()
except Exception as e:
    st.error(f"Não foi possível conectar ao Elasticsearch em `{ES_URL}`: {e}")
    st.stop()

with st.spinner("Verificando e indexando `laptops.csv` no Elasticsearch..."):
    indexed_count = init_index(es, force_reset=False)
    if indexed_count > 0:
        st.toast(f"{indexed_count} laptops importados do CSV com sucesso!", icon="🚀")

(
    all_manufacturers,
    all_categories,
    all_ram_gb,
    all_os,
    max_catalog_price,
    max_catalog_weight,
) = get_initial_facets(es)

# --- Sidebar: Status & Filtros ---
with st.sidebar:
    st.subheader("⚡ Status do Cluster")
    total_docs = es.count(index=INDEX_NAME)["count"]
    st.success(f"Elastic v{info['version']['number']} • **{total_docs}** docs")

    if st.button("🔄 Reimportar `laptops.csv`", use_container_width=True):
        count = init_index(es, force_reset=True)
        st.toast(f"Índice recriado com {count} laptops do CSV!", icon="✅")
        st.rerun()

    st.divider()
    st.subheader("🎛️ Filtros (`bool.filter`)")

    selected_manufacturers = st.multiselect(
        "Fabricante (`manufacturer`)", options=all_manufacturers
    )
    selected_categories = st.multiselect(
        "Categoria (`category`)", options=all_categories
    )
    selected_ram = st.multiselect(
        "Memória RAM em GB (`ram_gb`)",
        options=all_ram_gb,
        format_func=lambda x: f"{x} GB",
    )
    selected_os = st.multiselect("Sistema Operacional (`os`)", options=all_os)

    price_ceil = max(1000.0, float(round(max_catalog_price + 100, -2)))
    selected_price = st.slider(
        "Faixa de Preço (€)",
        min_value=0.0,
        max_value=price_ceil,
        value=(0.0, price_ceil),
        step=50.0,
    )

    weight_ceil = max(5.0, float(round(max_catalog_weight + 0.5, 1)))
    selected_weight = st.slider(
        "Peso (kg)",
        min_value=0.0,
        max_value=weight_ceil,
        value=(0.0, weight_ceil),
        step=0.1,
    )

    enable_fuzziness = st.checkbox(
        "Tolerar erros de digitação (`fuzziness: AUTO`)",
        value=True,
        help="Ex: buscar 'macbok', 'lenvo', 'geforse' ou 'ultrabok'",
    )

    sort_by = st.selectbox(
        "Ordenar por (`sort`)",
        [
            "Relevância (_score)",
            "Menor Preço (€)",
            "Maior Preço (€)",
            "Maior RAM (GB)",
            "Mais Leve (kg)",
        ],
    )

    page_size = st.select_slider(
        "Resultados exibidos (`size`)", options=[10, 25, 50, 100], value=25
    )

tab_search, tab_aggs, tab_crud, tab_dsl = st.tabs(
    [
        "🔎 Busca & Laptops",
        "📊 Agregações (Analytics)",
        "➕ Cadastrar / Excluir",
        "🧬 Inspecionar Query DSL",
    ]
)

with tab_search:
    search_query = st.text_input(
        "Pesquisar por modelo, processador (CPU), placa de vídeo (GPU), tela ou armazenamento:",
        placeholder="Ex: MacBook Retina, Core i7 SSD, GTX 1060, ThinkPad, Touchscreen 4K...",
    )

    query_dsl = build_es_query(
        search_text=search_query,
        manufacturers=selected_manufacturers,
        categories=selected_categories,
        ram_options=selected_ram,
        os_options=selected_os,
        price_range=selected_price,
        weight_range=selected_weight,
        fuzziness=enable_fuzziness,
        sort_option=sort_by,
        page_size=page_size,
    )

    response = es.search(index=INDEX_NAME, body=query_dsl)
    hits = response["hits"]["hits"]
    total_hits = response["hits"]["total"]["value"]
    took_ms = response["took"]
    aggs = response["aggregations"]
    price_stats = aggs["estatisticas_preco"]
    weight_stats = aggs["estatisticas_peso"]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Laptops Encontrados", f"{total_hits}")
    m2.metric("Tempo de Busca", f"{took_ms} ms")
    m3.metric(
        "Preço Médio (Filtro)",
        f"€ {price_stats['avg']:,.2f}" if price_stats["avg"] else "€ 0,00",
    )
    m4.metric(
        "Menor / Maior Preço",
        f"€ {price_stats['min'] or 0:,.0f} – € {price_stats['max'] or 0:,.0f}",
    )

    st.divider()

    if not hits:
        st.info("Nenhum laptop encontrado com os filtros atuais.")
    else:
        st.caption(f"Exibindo {len(hits)} de {total_hits} resultados.")
        for hit in hits:
            src = hit["_source"]
            hl = hit.get("highlight", {})
            score = hit.get("_score")

            title_html = hl.get("title", [src["title"]])[0]
            specs_html = hl.get("specs_summary", [src["specs_summary"]])[0]

            with st.container(border=True):
                col_main, col_meta = st.columns([3.2, 1])
                with col_main:
                    st.markdown(f"#### {title_html}", unsafe_allow_html=True)
                    st.markdown(specs_html, unsafe_allow_html=True)
                    st.markdown(
                        f"`Fabricante: {src['manufacturer']}` • "
                        f"`Categoria: {src['category']}` • "
                        f"`RAM: {src['ram']}` • "
                        f"`Armazenamento: {src['storage']}` • "
                        f"`OS: {src['os']}`"
                    )
                with col_meta:
                    st.markdown(f"### € {src['price_euros']:,.2f}")
                    st.write(f"⚖️ **Peso:** {src['weight']} | 🖥️ **Tela:** {src['screen_size']}")
                    if score is not None:
                        st.caption(f"Score BM25: `{score:.2f}` | ID: `{hit['_id']}`")
                    else:
                        st.caption(f"ID: `{hit['_id']}`")

with tab_aggs:
    st.subheader("📊 Agregações em Tempo Real sobre os Laptops Filtrados")
    st.write(
        "Gráficos gerados instantaneamente pelas `aggregations` do Elasticsearch respeitando sua busca e filtros."
    )

    c_agg1, c_agg2 = st.columns(2)

    with c_agg1:
        st.markdown("##### Top Fabricantes (`terms` em `manufacturer`)")
        man_buckets = aggs["por_fabricante"]["buckets"]
        if man_buckets:
            df_man = pd.DataFrame(man_buckets).rename(
                columns={"key": "Fabricante", "doc_count": "Laptops"}
            )
            st.bar_chart(df_man.set_index("Fabricante"))
            st.dataframe(df_man, use_container_width=True, hide_index=True)

    with c_agg2:
        st.markdown("##### Distribuição por Faixa de Preço (`range` em `price_euros`)")
        range_buckets = aggs["faixas_preco"]["buckets"]
        if range_buckets:
            df_range = pd.DataFrame(range_buckets)[["key", "doc_count"]].rename(
                columns={"key": "Faixa de Preço", "doc_count": "Laptops"}
            )
            st.bar_chart(df_range.set_index("Faixa de Preço"))
            st.dataframe(df_range, use_container_width=True, hide_index=True)

    st.divider()
    c_agg3, c_agg4 = st.columns(2)

    with c_agg3:
        st.markdown("##### Laptops por Categoria (`terms` em `category`)")
        cat_buckets = aggs["por_categoria"]["buckets"]
        if cat_buckets:
            df_cat = pd.DataFrame(cat_buckets).rename(
                columns={"key": "Categoria", "doc_count": "Laptops"}
            )
            st.bar_chart(df_cat.set_index("Categoria"))
            st.dataframe(df_cat, use_container_width=True, hide_index=True)

    with c_agg4:
        st.markdown("##### Laptops por Memória RAM GB (`terms` em `ram_gb`)")
        ram_buckets = aggs["por_ram"]["buckets"]
        if ram_buckets:
            df_ram = pd.DataFrame(ram_buckets).rename(
                columns={"key": "RAM (GB)", "doc_count": "Laptops"}
            )
            df_ram["RAM (GB)"] = df_ram["RAM (GB)"].astype(str) + " GB"
            st.bar_chart(df_ram.set_index("RAM (GB)"))
            st.dataframe(df_ram, use_container_width=True, hide_index=True)

with tab_crud:
    col_add, col_del = st.columns([2, 1])

    with col_add:
        st.subheader("➕ Cadastrar Novo Laptop no Índice")
        with st.form("add_laptop_form", clear_on_submit=True):
            f1, f2, f3 = st.columns(3)
            new_man = f1.text_input("Fabricante*", value="Dell")
            new_model = f2.text_input("Modelo*", value="XPS 15 9530")
            new_cat = f3.selectbox(
                "Categoria*",
                options=all_categories if all_categories else ["Ultrabook", "Notebook", "Gaming"],
            )

            f4, f5, f6 = st.columns(3)
            new_cpu = f4.text_input("CPU*", value="Intel Core i7 13700H 2.4GHz")
            new_gpu = f5.text_input("GPU*", value="Nvidia GeForce RTX 4060")
            new_storage = f6.text_input("Armazenamento*", value="1TB SSD")

            f7, f8, f9, f10 = st.columns(4)
            new_ram_gb = f7.selectbox("RAM (GB)*", options=[4, 8, 12, 16, 24, 32, 64], index=3)
            new_screen_in = f8.number_input("Tela (pol)*", value=15.6, step=0.1)
            new_weight_kg = f9.number_input("Peso (kg)*", value=1.86, step=0.05)
            new_price = f10.number_input("Preço (€)*", min_value=50.0, value=1899.00, step=50.0)

            f11, f12 = st.columns(2)
            new_screen_desc = f11.text_input("Resolução / Tipo de Tela", value="OLED 3.5K 3456x2160")
            new_os = f12.text_input("Sistema Operacional", value="Windows")

            submitted = st.form_submit_button("Indexar Laptop", type="primary")
            if submitted:
                title = f"{new_man.strip()} {new_model.strip()}"
                screen_size_str = f'{new_screen_in}"'
                ram_str = f"{new_ram_gb}GB"
                weight_str = f"{new_weight_kg}kg"
                specs_summary = (
                    f"{new_cat} | Tela {screen_size_str} {new_screen_desc} | "
                    f"CPU: {new_cpu} | RAM: {ram_str} | Armazenamento: {new_storage} | "
                    f"GPU: {new_gpu} | OS: {new_os} | Peso: {weight_str}"
                )
                doc = {
                    "title": title,
                    "manufacturer": new_man.strip(),
                    "model_name": new_model.strip(),
                    "category": new_cat,
                    "screen_size": screen_size_str,
                    "screen_inches": float(new_screen_in),
                    "screen": new_screen_desc.strip(),
                    "cpu": new_cpu.strip(),
                    "ram": ram_str,
                    "ram_gb": int(new_ram_gb),
                    "storage": new_storage.strip(),
                    "gpu": new_gpu.strip(),
                    "os": new_os.strip(),
                    "os_version": "",
                    "weight": weight_str,
                    "weight_kg": float(new_weight_kg),
                    "price_euros": float(new_price),
                    "specs_summary": specs_summary,
                }
                res = es.index(index=INDEX_NAME, document=doc, refresh=True)
                st.success(f"Laptop indexado com sucesso! ID: `{res['_id']}`")
                st.rerun()

    with col_del:
        st.subheader("🗑️ Remover Laptop por ID")
        doc_id_to_delete = st.text_input("ID do Documento:")
        if st.button("Excluir Documento", type="secondary"):
            if doc_id_to_delete.strip():
                try:
                    es.delete(
                        index=INDEX_NAME, id=doc_id_to_delete.strip(), refresh=True
                    )
                    st.success(f"Laptop ID `{doc_id_to_delete}` removido!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao remover: {e}")
            else:
                st.warning("Informe um ID válido.")

with tab_dsl:
    st.subheader("🧬 Query DSL Enviada & Mapeamento do Índice")
    col_q, col_m = st.columns(2)
    with col_q:
        st.markdown("**Query JSON enviada ao endpoint `/_search`:**")
        st.json(query_dsl)
    with col_m:
        st.markdown(f"**Mapping atual do índice `{INDEX_NAME}`:**")
        mapping = es.indices.get_mapping(index=INDEX_NAME)
        st.json(mapping.body)
