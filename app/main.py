import streamlit as st

from es_service import LaptopRepository
from queries import build_search_query
from ui import (
    render_aggregations_tab,
    render_crud_tab,
    render_dsl_tab,
    render_search_results,
    render_sidebar,
)

st.set_page_config(
    page_title="Laptops Explorer - Elasticsearch",
    page_icon="💻",
    layout="wide",
)


@st.cache_resource
def get_repository() -> LaptopRepository:
    return LaptopRepository()


def main() -> None:
    st.title("💻 Catálogo de Laptops (`laptops.csv`) no Elasticsearch")
    st.caption(
        "Base real com **1.303 laptops** indexada via **Bulk API** com **Full-Text Search (BM25)**, "
        "**Fuzzy Search**, **Highlighting**, **Bool Filters** e **Aggregations**."
    )

    repo = get_repository()

    try:
        info = repo.get_cluster_info()
    except Exception as exc:
        st.error(f"Não foi possível conectar ao Elasticsearch em `{repo.es_url}`: {exc}")
        st.stop()

    with st.spinner("Verificando e indexando `laptops.csv` no Elasticsearch..."):
        indexed_count = repo.init_index(force_reset=False)
        if indexed_count > 0:
            st.toast(f"{indexed_count} laptops importados do CSV com sucesso!", icon="🚀")

    facets = repo.get_facets()
    filters = render_sidebar(repo, info["version"]["number"], facets)

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
        query_dsl = build_search_query(search_text=search_query, **filters)
        response = repo.search(query_dsl)
        render_search_results(response)

    with tab_aggs:
        render_aggregations_tab(response["aggregations"])

    with tab_crud:
        render_crud_tab(repo, facets.categories)

    with tab_dsl:
        render_dsl_tab(repo, query_dsl)


if __name__ == "__main__":
    main()
