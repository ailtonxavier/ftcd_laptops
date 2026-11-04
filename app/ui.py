import pandas as pd
import streamlit as st

from config import SORT_OPTIONS
from es_service import CatalogFacets, LaptopRepository
from seed_data import build_laptop_doc


def render_sidebar(
    repo: LaptopRepository, cluster_version: str, facets: CatalogFacets
) -> dict:
    """Renderiza a barra lateral de status e filtros, retornando os filtros selecionados."""
    with st.sidebar:
        st.subheader("⚡ Status do Cluster")
        total_docs = repo.count_documents()
        st.success(f"Elastic v{cluster_version} • **{total_docs}** docs")

        if st.button("🔄 Reimportar `laptops.csv`", use_container_width=True):
            count = repo.init_index(force_reset=True)
            st.toast(f"Índice recriado com {count} laptops do CSV!", icon="✅")
            st.rerun()

        st.divider()
        st.subheader("🎛️ Filtros (`bool.filter`)")

        manufacturers = st.multiselect(
            "Fabricante (`manufacturer`)", options=facets.manufacturers
        )
        categories = st.multiselect(
            "Categoria (`category`)", options=facets.categories
        )
        ram_options = st.multiselect(
            "Memória RAM em GB (`ram_gb`)",
            options=facets.ram_gb,
            format_func=lambda x: f"{x} GB",
        )
        os_options = st.multiselect(
            "Sistema Operacional (`os`)", options=facets.os_list
        )

        price_ceil = max(1000.0, float(round(facets.max_price + 100, -2)))
        price_range = st.slider(
            "Faixa de Preço (€)",
            min_value=0.0,
            max_value=price_ceil,
            value=(0.0, price_ceil),
            step=50.0,
        )

        weight_ceil = max(5.0, float(round(facets.max_weight + 0.5, 1)))
        weight_range = st.slider(
            "Peso (kg)",
            min_value=0.0,
            max_value=weight_ceil,
            value=(0.0, weight_ceil),
            step=0.1,
        )

        fuzziness = st.checkbox(
            "Tolerar erros de digitação (`fuzziness: AUTO`)",
            value=True,
            help="Ex: buscar 'macbok', 'lenvo', 'geforse' ou 'ultrabok'",
        )

        sort_option = st.selectbox("Ordenar por (`sort`)", list(SORT_OPTIONS.keys()))
        page_size = st.select_slider(
            "Resultados exibidos (`size`)", options=[10, 25, 50, 100], value=25
        )

    return {
        "manufacturers": manufacturers,
        "categories": categories,
        "ram_options": ram_options,
        "os_options": os_options,
        "price_range": price_range,
        "weight_range": weight_range,
        "fuzziness": fuzziness,
        "sort_option": sort_option,
        "page_size": page_size,
    }


def _render_laptop_card(hit: dict) -> None:
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
            score_txt = f"Score BM25: `{score:.2f}` | " if score is not None else ""
            st.caption(f"{score_txt}ID: `{hit['_id']}`")


def render_search_results(response: dict) -> None:
    """Renderiza métricas e cards de resultado da busca."""
    hits = response["hits"]["hits"]
    total_hits = response["hits"]["total"]["value"]
    took_ms = response["took"]
    price_stats = response["aggregations"]["estatisticas_preco"]

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
        return

    st.caption(f"Exibindo {len(hits)} de {total_hits} resultados.")
    for hit in hits:
        _render_laptop_card(hit)


def _render_bucket_chart(
    title: str, buckets: list[dict], label_col: str, suffix: str = ""
) -> None:
    st.markdown(f"##### {title}")
    if not buckets:
        st.info("Sem dados para exibir.")
        return

    df = pd.DataFrame(buckets)[["key", "doc_count"]].rename(
        columns={"key": label_col, "doc_count": "Laptops"}
    )
    if suffix:
        df[label_col] = df[label_col].astype(str) + suffix

    st.bar_chart(df.set_index(label_col))
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_aggregations_tab(aggs: dict) -> None:
    """Renderiza gráficos e tabelas de agregações do Elasticsearch."""
    st.subheader("📊 Agregações em Tempo Real sobre os Laptops Filtrados")
    st.write(
        "Gráficos gerados instantaneamente pelas `aggregations` do Elasticsearch respeitando sua busca e filtros."
    )

    c1, c2 = st.columns(2)
    with c1:
        _render_bucket_chart(
            "Top Fabricantes (`terms` em `manufacturer`)",
            aggs["por_fabricante"]["buckets"],
            "Fabricante",
        )
    with c2:
        _render_bucket_chart(
            "Distribuição por Faixa de Preço (`range` em `price_euros`)",
            aggs["faixas_preco"]["buckets"],
            "Faixa de Preço",
        )

    st.divider()
    c3, c4 = st.columns(2)
    with c3:
        _render_bucket_chart(
            "Laptops por Categoria (`terms` em `category`)",
            aggs["por_categoria"]["buckets"],
            "Categoria",
        )
    with c4:
        _render_bucket_chart(
            "Laptops por Memória RAM GB (`terms` em `ram_gb`)",
            aggs["por_ram"]["buckets"],
            "RAM (GB)",
            suffix=" GB",
        )


def render_crud_tab(repo: LaptopRepository, categories: list[str]) -> None:
    """Renderiza os formulários de cadastro e exclusão de laptops."""
    col_add, col_del = st.columns([2, 1])

    with col_add:
        st.subheader("➕ Cadastrar Novo Laptop no Índice")
        with st.form("add_laptop_form", clear_on_submit=True):
            f1, f2, f3 = st.columns(3)
            man = f1.text_input("Fabricante*", value="Dell")
            model = f2.text_input("Modelo*", value="XPS 15 9530")
            cat = f3.selectbox(
                "Categoria*",
                options=categories or ["Ultrabook", "Notebook", "Gaming"],
            )

            f4, f5, f6 = st.columns(3)
            cpu = f4.text_input("CPU*", value="Intel Core i7 13700H 2.4GHz")
            gpu = f5.text_input("GPU*", value="Nvidia GeForce RTX 4060")
            storage = f6.text_input("Armazenamento*", value="1TB SSD")

            f7, f8, f9, f10 = st.columns(4)
            ram_gb = f7.selectbox(
                "RAM (GB)*", options=[4, 8, 12, 16, 24, 32, 64], index=3
            )
            screen_in = f8.number_input("Tela (pol)*", value=15.6, step=0.1)
            weight_kg = f9.number_input("Peso (kg)*", value=1.86, step=0.05)
            price = f10.number_input(
                "Preço (€)*", min_value=50.0, value=1899.00, step=50.0
            )

            f11, f12 = st.columns(2)
            screen_desc = f11.text_input(
                "Resolução / Tipo de Tela", value="OLED 3.5K 3456x2160"
            )
            os_name = f12.text_input("Sistema Operacional", value="Windows")

            if st.form_submit_button("Indexar Laptop", type="primary"):
                doc = build_laptop_doc(
                    manufacturer=man.strip(),
                    model_name=model.strip(),
                    category=cat,
                    screen_size=f'{screen_in}"',
                    screen_inches=float(screen_in),
                    screen=screen_desc.strip(),
                    cpu=cpu.strip(),
                    ram=f"{ram_gb}GB",
                    ram_gb=int(ram_gb),
                    storage=storage.strip(),
                    gpu=gpu.strip(),
                    os_name=os_name.strip(),
                    os_version="",
                    weight=f"{weight_kg}kg",
                    weight_kg=float(weight_kg),
                    price_euros=float(price),
                )
                doc_id = repo.index_laptop(doc)
                st.success(f"Laptop indexado com sucesso! ID: `{doc_id}`")
                st.rerun()

    with col_del:
        st.subheader("🗑️ Remover Laptop por ID")
        doc_id = st.text_input("ID do Documento:")
        if st.button("Excluir Documento", type="secondary"):
            if not doc_id.strip():
                st.warning("Informe um ID válido.")
                return
            try:
                repo.delete_laptop(doc_id.strip())
                st.success(f"Laptop ID `{doc_id}` removido!")
                st.rerun()
            except Exception as exc:
                st.error(f"Erro ao remover: {exc}")


def render_dsl_tab(repo: LaptopRepository, query_dsl: dict) -> None:
    """Renderiza a aba de inspeção da Query DSL e do Mapping do índice."""
    st.subheader("🧬 Query DSL Enviada & Mapeamento do Índice")
    col_q, col_m = st.columns(2)
    with col_q:
        st.markdown("**Query JSON enviada ao endpoint `/_search`:**")
        st.json(query_dsl)
    with col_m:
        st.markdown(f"**Mapping atual do índice `{repo.index_name}`:**")
        st.json(repo.get_mapping())

