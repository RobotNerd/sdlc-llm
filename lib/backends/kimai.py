"""Kimai through its REST API, which the time-tracking hook uses to start and stop timesheet entries."""

from datetime import datetime

from lib.backends.rest import RestClient


class KimaiApi:
    def __init__(self, url, api_token):
        self.client = RestClient("Kimai", url, api_token)

    def start_entry(self, project_id, activity_id, begin=None):
        """Start a running entry and return it. Kimai reads a begin time without a zone as the user's local time."""
        begin = begin or datetime.now()
        body = {"activity": activity_id, "begin": begin.strftime("%Y-%m-%dT%H:%M:%S"), "project": project_id}
        return self.client.request("start entry", "POST", "/api/timesheets", body)

    def stop_entry(self, entry_id, end=None):
        """Stop a running entry now, or at `end`, a time Kimai reads as the user's local time."""
        if end is None:
            return self.client.request("stop entry", "PATCH", f"/api/timesheets/{entry_id}/stop")
        body = {"end": end.astimezone().strftime("%Y-%m-%dT%H:%M:%S")}
        return self.client.request("stop entry", "PATCH", f"/api/timesheets/{entry_id}", body)
