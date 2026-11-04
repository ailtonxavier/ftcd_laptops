from dataclasses import dataclass
from elasticsearch import Elasticsearch, helpers

from config import ES_URL, INDEX_NAME, INDEX_SETTINGS
from queries import build_facets_query
from seed_data import load_laptops_from_csv


@dataclass
class CatalogFacets:
    manufacturers: list[str]
    categories: list[str]
    ram_gb: list[int]
    os_list: list[str]
    max_price: float
    max_weight: float


class LaptopRepository:
    """Camada de acesso a dados responsável por toda comunicação com o Elasticsearch."""

    def __init__(self, es_url: str = ES_URL, index_name: str = INDEX_NAME):
        self.es_url = es_url
        self.index_name = index_name
        self.client = Elasticsearch(es_url, request_timeout=15)

    def get_cluster_info(self) -> dict:
        return dict(self.client.info())

    def count_documents(self) -> int:
        return self.client.count(index=self.index_name)["count"]

    def init_index(self, force_reset: bool = False) -> int:
        if force_reset and self.client.indices.exists(index=self.index_name):
            self.client.indices.delete(index=self.index_name)

        if self.client.indices.exists(index=self.index_name):
            return 0

        self.client.indices.create(index=self.index_name, body=INDEX_SETTINGS)
        laptops = load_laptops_from_csv()
        actions = [
            {
                "_index": self.index_name,
                "_id": str(idx),
                "_source": doc,
            }
            for idx, doc in enumerate(laptops, start=1)
        ]
        helpers.bulk(self.client, actions, refresh=True)
        return len(laptops)

    def get_facets(self) -> CatalogFacets:
        res = self.client.search(index=self.index_name, body=build_facets_query())
        aggs = res["aggregations"]
        return CatalogFacets(
            manufacturers=[b["key"] for b in aggs["manufacturers"]["buckets"]],
            categories=[b["key"] for b in aggs["categories"]["buckets"]],
            ram_gb=[int(b["key"]) for b in aggs["ram_gb"]["buckets"]],
            os_list=[b["key"] for b in aggs["os"]["buckets"]],
            max_price=float(aggs["max_price"]["value"] or 6500.0),
            max_weight=float(aggs["max_weight"]["value"] or 5.0),
        )

    def search(self, query_dsl: dict) -> dict:
        return dict(self.client.search(index=self.index_name, body=query_dsl))

    def index_laptop(self, doc: dict) -> str:
        res = self.client.index(index=self.index_name, document=doc, refresh=True)
        return res["_id"]

    def delete_laptop(self, doc_id: str) -> None:
        self.client.delete(index=self.index_name, id=doc_id, refresh=True)

    def get_mapping(self) -> dict:
        return dict(self.client.indices.get_mapping(index=self.index_name).body)

