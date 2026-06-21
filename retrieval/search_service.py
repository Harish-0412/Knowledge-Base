from query_router import QueryRoute, QueryRouter
from retriever import COMPATIBILITY_COLLECTION, DOMAIN_COLLECTION, Retriever


MIN_SIMILARITY = 0.50
MAX_SCORE_DROP = 0.10


class SearchService:
    def __init__(self, retriever=None, router=None):
        self.retriever = retriever or Retriever()
        self.router = router or QueryRouter()

    def verify_collections(self):
        return self.retriever.verify_collections()

    def search_layer1(self, query, top_k=5, query_vector=None):
        return self.retriever.search(DOMAIN_COLLECTION, query, top_k, query_vector)

    def search_layer3(self, query, top_k=5, query_vector=None):
        return self.retriever.search(COMPATIBILITY_COLLECTION, query, top_k, query_vector)

    @staticmethod
    def select_relevant(results, top_k=5):
        if not results:
            return []
        ordered = sorted(results, key=lambda item: item["score"], reverse=True)
        cutoff = max(MIN_SIMILARITY, ordered[0]["score"] - MAX_SCORE_DROP)
        return [result for result in ordered[:top_k] if result["score"] >= cutoff]

    def search_combined(self, query, top_k=5):
        query_vector = self.retriever.embed_query(query)
        results = []
        errors = []
        for collection_name in (DOMAIN_COLLECTION, COMPATIBILITY_COLLECTION):
            try:
                results.extend(
                    self.retriever.search(collection_name, query, top_k, query_vector)
                )
            except Exception as exc:
                errors.append(str(exc))
        results.sort(key=lambda item: item["score"], reverse=True)
        return self.select_relevant(results, top_k), errors

    def search(self, query, top_k=5, route=None):
        selected_route = QueryRoute(route) if route else self.router.route(query)
        errors = []
        results = []
        try:
            if selected_route == QueryRoute.DOMAIN:
                results = self.select_relevant(self.search_layer1(query, top_k), top_k)
            elif selected_route == QueryRoute.COMPATIBILITY:
                results = self.select_relevant(self.search_layer3(query, top_k), top_k)
            else:
                results, errors = self.search_combined(query, top_k)
        except Exception as exc:
            errors.append(str(exc))
        return {
            "query": query,
            "route": selected_route.value,
            "top_k": top_k,
            "results": results,
            "errors": errors,
        }
