"""Outline through its REST API. The prose skills use lib/references/backends/outline.md instead."""

from lib.backends.rest import RestClient

# Outline's largest page size.
PAGE_SIZE = 100


class OutlineApi:
    def __init__(self, url, api_key):
        self.client = RestClient("Outline", f"{url.rstrip('/')}/api", api_key)

    def list_collections(self):
        collections, offset = [], 0
        while True:
            body = {"limit": PAGE_SIZE, "offset": offset}
            page = self.client.request("list collections", "POST", "/collections.list", body)["data"]
            collections.extend(page)
            if len(page) < PAGE_SIZE:
                return collections
            offset += PAGE_SIZE

    def create_collection(self, name):
        return self.client.request("create collection", "POST", "/collections.create", {"name": name})["data"]

    def document_tree(self, collection_id):
        """Return the collection's published docs as nested {id, title, children} nodes."""
        return self.client.request("read the collection's docs", "POST", "/collections.documents", {"id": collection_id})[
            "data"
        ]

    def create_document(self, title, text, collection_id, parent_document_id=None):
        body = {"collectionId": collection_id, "publish": True, "text": text, "title": title}
        if parent_document_id:
            body["parentDocumentId"] = parent_document_id
        return self.client.request(f"create doc {title!r}", "POST", "/documents.create", body)["data"]
