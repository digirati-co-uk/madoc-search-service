from django.contrib.postgres.aggregates import StringAgg
from django.contrib.postgres.search import (
    SearchQuery, SearchRank, SearchVector, TrigramSimilarity,
)
from django.db import models


class IndexableManager(models.Manager):
    def search(self, search_text, language="english"):
        # search_vectors = self.search_vector
        search_query = SearchQuery(
            search_text, config=language
        )
        search_rank = SearchRank('search_vector', search_query)
        trigram_similarity = TrigramSimilarity(
            'indexable', search_text
        )
        qs = (
            self.get_queryset()
            .filter(search_vector=search_query)
            .annotate(rank=search_rank + trigram_similarity)
            .order_by('-rank')
        )
        return qs
