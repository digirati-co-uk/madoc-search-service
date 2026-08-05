from locust import HttpUser, task, between

class SearchUser(HttpUser):
    # Wait between 1 and 3 seconds between tasks to simulate realistic user behavior
    wait_time = between(1, 3)

    @task(3)  # This task runs 3x more often than a @task(1)
    def cold_global_facet(self):
        payload = {
            "facet_types": ["metadata"]
        }
        self.client.post(
            "/api/search/search", 
            json=payload, 
            name="1. Cold Global Facet"
        )

    @task(2)
    def text_search_facets(self):
        payload = {
            "fulltext": "History",
            "facet_types": ["metadata"]
        }
        self.client.post(
            "/api/search/search", 
            json=payload, 
            name="2. Text Search + Facets"
        )

    @task(2)
    def deep_filtered_facets(self):
        payload = {
            "facets": [
                {"type": "metadata", "subtype": "Author", "value": "John Smith"}
            ],
            "facet_types": ["metadata"]
        }
        self.client.post(
            "/api/search/search", 
            json=payload, 
            name="3. Deep Filtered Facets"
        )

    @task(1)
    def pagination(self):
        payload = {
            "page": 20
        }
        self.client.post(
            "/api/search/search", 
            json=payload, 
            name="4. Pagination"
        )
