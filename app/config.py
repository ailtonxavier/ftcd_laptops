import os

ES_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
INDEX_NAME = "laptops_catalog"
CSV_PATH = os.path.join(os.path.dirname(__file__), "laptops.csv")

SORT_OPTIONS = {
    "Relevância (_score)": ["_score"],
    "Menor Preço (€)": [{"price_euros": "asc"}],
    "Maior Preço (€)": [{"price_euros": "desc"}],
    "Maior RAM (GB)": [{"ram_gb": "desc"}],
    "Mais Leve (kg)": [{"weight_kg": "asc"}],
}

TEXT_WITH_KEYWORD = {
    "type": "text",
    "fields": {"keyword": {"type": "keyword"}},
}

INDEX_SETTINGS = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
    },
    "mappings": {
        "properties": {
            "title": TEXT_WITH_KEYWORD,
            "manufacturer": {"type": "keyword"},
            "model_name": TEXT_WITH_KEYWORD,
            "category": {"type": "keyword"},
            "screen_size": {"type": "keyword"},
            "screen_inches": {"type": "float"},
            "screen": TEXT_WITH_KEYWORD,
            "cpu": TEXT_WITH_KEYWORD,
            "ram": {"type": "keyword"},
            "ram_gb": {"type": "integer"},
            "storage": TEXT_WITH_KEYWORD,
            "gpu": TEXT_WITH_KEYWORD,
            "os": {"type": "keyword"},
            "os_version": {"type": "keyword"},
            "weight": {"type": "keyword"},
            "weight_kg": {"type": "float"},
            "price_euros": {"type": "float"},
            "specs_summary": {"type": "text"},
        }
    },
}

