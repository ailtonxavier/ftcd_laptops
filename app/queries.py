from config import SORT_OPTIONS

SEARCH_FIELDS = [
    "title^3",
    "model_name^2",
    "cpu^2",
    "gpu^2",
    "storage",
    "screen",
    "specs_summary",
]

PRICE_RANGES = [
    {"key": "Até € 500", "to": 500},
    {"key": "€ 500 - € 1.000", "from": 500, "to": 1000},
    {"key": "€ 1.000 - € 1.500", "from": 1000, "to": 1500},
    {"key": "€ 1.500 - € 2.500", "from": 1500, "to": 2500},
    {"key": "Acima de € 2.500", "from": 2500},
]

HIGHLIGHT_TAG = (
    "<mark style='background-color: #ffe066; color: #111; "
    "padding: 1px 4px; border-radius: 3px;'>"
)


def build_facets_query() -> dict:
    """Retorna a query DSL para carregar as opções iniciais de filtros."""
    return {
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
    }


def build_search_query(
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
    """Constrói a Query DSL completa com busca full-text, filtros, highlight e agregações."""
    text = search_text.strip()
    if text:
        multi_match = {
            "query": text,
            "fields": SEARCH_FIELDS,
            "operator": "or",
        }
        if fuzziness:
            multi_match["fuzziness"] = "AUTO"
        must_clauses = [{"multi_match": multi_match}]
    else:
        must_clauses = [{"match_all": {}}]

    terms_filters = {
        "manufacturer": manufacturers,
        "category": categories,
        "ram_gb": ram_options,
        "os": os_options,
    }
    filter_clauses = [
        {"terms": {field: values}}
        for field, values in terms_filters.items()
        if values
    ]
    filter_clauses.extend(
        [
            {"range": {"price_euros": {"gte": price_range[0], "lte": price_range[1]}}},
            {"range": {"weight_kg": {"gte": weight_range[0], "lte": weight_range[1]}}},
        ]
    )

    return {
        "size": page_size,
        "query": {"bool": {"must": must_clauses, "filter": filter_clauses}},
        "sort": SORT_OPTIONS.get(sort_option, ["_score"]),
        "highlight": {
            "pre_tags": [HIGHLIGHT_TAG],
            "post_tags": ["</mark>"],
            "fields": {f: {} for f in ("title", "specs_summary", "cpu", "gpu")},
        },
        "aggs": {
            "por_fabricante": {"terms": {"field": "manufacturer", "size": 20}},
            "por_categoria": {"terms": {"field": "category", "size": 10}},
            "por_ram": {"terms": {"field": "ram_gb", "size": 10}},
            "por_os": {"terms": {"field": "os", "size": 10}},
            "estatisticas_preco": {"stats": {"field": "price_euros"}},
            "estatisticas_peso": {"stats": {"field": "weight_kg"}},
            "faixas_preco": {
                "range": {"field": "price_euros", "ranges": PRICE_RANGES}
            },
        },
    }

