"""Stateful fakes of the Kaneo and Outline REST APIs, covering the calls setup makes."""

import itertools
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

# Kaneo gives a new project these columns. The slug comes from the name.
DEFAULT_KANEO_COLUMNS = (("To Do", False), ("In Progress", False), ("In Review", False), ("Done", True))


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class FakeService:
    """Answers each request from handle(), records it, and can be made to fail."""

    def __init__(self):
        self.requests = []
        self.fail_with = None
        self.ids = (f"id{number:04d}" for number in itertools.count(1))
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def handle_any(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length)) if length else None
                url = urlparse(self.path)
                fake.requests.append({"body": body, "headers": dict(self.headers), "method": self.command, "path": url.path})
                if fake.fail_with:
                    status, payload = fake.fail_with, "internal error"
                else:
                    status, payload = fake.handle(self.command, url.path, parse_qs(url.query), body)
                encoded = (payload if isinstance(payload, str) else json.dumps(payload)).encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            do_GET = do_POST = do_PUT = handle_any

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, args=(0.05,), daemon=True).start()

    def next_id(self):
        return next(self.ids)

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class FakeKaneo(FakeService):
    def __init__(self):
        super().__init__()
        self.projects = []
        self.columns = {}
        self.labels = []

    def writes(self):
        return [request for request in self.requests if request["method"] != "GET"]

    def add_project(self, workspace_id, name, slug):
        project = {"id": self.next_id(), "name": name, "slug": slug, "workspaceId": workspace_id}
        self.projects.append(project)
        self.columns[project["id"]] = [
            self.make_column(project["id"], name, is_final, position)
            for position, (name, is_final) in enumerate(DEFAULT_KANEO_COLUMNS)
        ]
        return project

    def make_column(self, project_id, name, is_final, position):
        return {"id": self.next_id(), "isFinal": is_final, "name": name, "position": position,
                "projectId": project_id, "slug": slugify(name)}

    def add_label(self, workspace_id, name, task_id=None):
        label = {"color": "#000000", "id": self.next_id(), "name": name, "taskId": task_id, "workspaceId": workspace_id}
        self.labels.append(label)
        return label

    def handle(self, method, path, query, body):
        if path == "/api/project" and method == "GET":
            return 200, [project for project in self.projects if project["workspaceId"] == query["workspaceId"][0]]
        if path == "/api/project" and method == "POST":
            return 200, self.add_project(body["workspaceId"], body["name"], body["slug"])
        if match := re.fullmatch(r"/api/column/reorder/(\w+)", path):
            positions = {column["id"]: column["position"] for column in body["columns"]}
            for column in self.columns[match[1]]:
                column["position"] = positions[column["id"]]
            return 200, {"success": True}
        if match := re.fullmatch(r"/api/column/(\w+)", path):
            if method == "GET":
                return 200, sorted(self.columns.get(match[1], []), key=lambda column: column["position"])
            if method == "POST":
                columns = self.columns[match[1]]
                column = self.make_column(match[1], body["name"], body.get("isFinal", False), len(columns))
                columns.append(column)
                return 200, column
            if method == "PUT":
                column = next(column for columns in self.columns.values() for column in columns if column["id"] == match[1])
                column.update(body)
                return 200, column
        if match := re.fullmatch(r"/api/label/workspace/(\w+)", path):
            return 200, [label for label in self.labels if label["workspaceId"] == match[1]]
        if path == "/api/label" and method == "POST":
            return 200, self.add_label(body["workspaceId"], body["name"])
        return 404, "Not found"


class FakeOutline(FakeService):
    def __init__(self):
        super().__init__()
        self.collections = []
        self.documents = []

    def writes(self):
        return [request for request in self.requests if not request["path"].endswith((".list", ".documents", ".info"))]

    def add_collection(self, name):
        collection = {"id": self.next_id(), "name": name}
        self.collections.append(collection)
        return collection

    def add_document(self, collection_id, title, text, parent_id=None):
        document = {"collectionId": collection_id, "id": self.next_id(), "parentDocumentId": parent_id,
                    "text": text, "title": title}
        self.documents.append(document)
        return document

    def tree(self, collection_id, parent_id=None):
        return [
            {"children": self.tree(collection_id, document["id"]), "id": document["id"], "title": document["title"]}
            for document in self.documents
            if document["collectionId"] == collection_id and document["parentDocumentId"] == parent_id
        ]

    def handle(self, method, path, query, body):
        if path == "/api/collections.list":
            page = self.collections[body["offset"] : body["offset"] + body["limit"]]
            return 200, {"data": page}
        if path == "/api/collections.create":
            return 200, {"data": self.add_collection(body["name"])}
        if path == "/api/collections.documents":
            return 200, {"data": self.tree(body["id"])}
        if path == "/api/documents.create":
            document = self.add_document(body["collectionId"], body["title"], body["text"], body.get("parentDocumentId"))
            return 200, {"data": document}
        return 404, {"error": "not_found"}
