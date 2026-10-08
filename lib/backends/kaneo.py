"""Kaneo through its REST API. The prose skills use lib/references/backends/kaneo.md instead."""

from lib.backends.rest import RestClient


class KaneoApi:
    def __init__(self, url, api_key):
        self.client = RestClient("Kaneo", f"{url.rstrip('/')}/api", api_key)

    def list_projects(self, workspace_id):
        return self.client.request("list projects", "GET", "/project", query={"workspaceId": workspace_id})

    def create_project(self, workspace_id, name, slug, icon):
        body = {"icon": icon, "name": name, "slug": slug, "workspaceId": workspace_id}
        return self.client.request("create project", "POST", "/project", body)

    def list_columns(self, project_id):
        return self.client.request("list columns", "GET", f"/column/{project_id}")

    def create_column(self, project_id, name, is_final):
        body = {"isFinal": is_final, "name": name}
        return self.client.request(f"create column {name!r}", "POST", f"/column/{project_id}", body)

    def mark_column_final(self, column_id, name):
        return self.client.request(f"mark column {name!r} final", "PUT", f"/column/{column_id}", {"isFinal": True})

    def reorder_columns(self, project_id, column_ids):
        body = {"columns": [{"id": column_id, "position": index} for index, column_id in enumerate(column_ids)]}
        return self.client.request("reorder columns", "PUT", f"/column/reorder/{project_id}", body)

    def list_workspace_labels(self, workspace_id):
        return self.client.request("list labels", "GET", f"/label/workspace/{workspace_id}")

    def create_label(self, workspace_id, name, color):
        body = {"color": color, "name": name, "workspaceId": workspace_id}
        return self.client.request(f"create label {name!r}", "POST", "/label", body)
