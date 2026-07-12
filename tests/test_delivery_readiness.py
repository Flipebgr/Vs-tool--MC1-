"""Validações pequenas para a preparação de entrega."""

import unittest

import app
from services.event_chain_service import build_event_chain
from services.filter_service import build_filtered_elements
from services.graph_service import load_graph


class DeliveryReadinessTests(unittest.TestCase):
    def test_app_import_and_dash_endpoints(self):
        client = app.app.server.test_client()

        for endpoint in ("/", "/_dash-layout", "/_dash-dependencies"):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(client.get(endpoint).status_code, 200)

    def test_callback_count(self):
        self.assertEqual(len(app.app.callback_map), 16)

    def test_layout_has_82_unique_ids(self):
        ids = [
            component.id
            for component in app.app.layout._traverse()
            if getattr(component, "id", None) is not None
        ]

        self.assertEqual(len(ids), 82)
        self.assertEqual(len(set(ids)), 82)

    def test_event_373902_chain_sizes(self):
        self.assertEqual(len(build_event_chain(373902, "core")["events"]), 8)
        self.assertEqual(len(build_event_chain(373902, "all")["events"]), 191)

    def test_led_by_filter_sizes(self):
        elements = build_filtered_elements(load_graph(), relation_filter=["led_by"])
        nodes = [element for element in elements if "id" in element["data"]]
        edges = [element for element in elements if "source" in element["data"]]

        self.assertEqual(len(nodes), 10)
        self.assertEqual(len(edges), 5)


if __name__ == "__main__":
    unittest.main()
