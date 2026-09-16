from datetime import date
from unittest.mock import patch

import src.asana.client
from test.impl.base_test_case_class import BaseClass

asana_api_client = src.asana.client.AsanaClient.singleton().asana_api_client


class TestOutOfOffice(BaseClass):
    TODAY = date(2026, 9, 16)

    def test_requires_ids(self):
        with self.assertRaises(ValueError):
            src.asana.client.out_of_office_until("", "ws", self.TODAY)
        with self.assertRaises(ValueError):
            src.asana.client.out_of_office_until("user", "", self.TODAY)

    def test_queries_entries_overlapping_today(self):
        with patch.object(
            asana_api_client, "get_collection", return_value=iter([])
        ) as get_collection:
            self.assertIsNone(
                src.asana.client.out_of_office_until("123", "456", self.TODAY)
            )
            get_collection.assert_called_once_with(
                "/ooo_entries",
                {
                    "user": "123",
                    "workspace": "456",
                    "start_date": "2026-09-16",
                    "end_date": "2026-09-16",
                },
                fields=["start_date", "end_date"],
            )

    def test_active_entry_returns_its_end(self):
        entries = [{"start_date": "2026-09-15", "end_date": "2026-09-22"}]
        with patch.object(
            asana_api_client,
            "get_collection",
            side_effect=lambda *args, **kwargs: iter(entries),
        ):
            self.assertEqual(
                src.asana.client.out_of_office_until("123", "456", self.TODAY),
                date(2026, 9, 22),
            )

    def test_open_ended_entry(self):
        entries = [{"start_date": "2026-09-15", "end_date": None}]
        with patch.object(
            asana_api_client, "get_collection", return_value=iter(entries)
        ):
            self.assertEqual(
                src.asana.client.out_of_office_until("123", "456", self.TODAY), date.max
            )

    def test_entries_outside_today_are_ignored(self):
        entries = [
            {"start_date": "2026-09-01", "end_date": "2026-09-10"},
            {"start_date": "2026-09-20", "end_date": "2026-09-25"},
        ]
        with patch.object(
            asana_api_client, "get_collection", return_value=iter(entries)
        ):
            self.assertIsNone(
                src.asana.client.out_of_office_until("123", "456", self.TODAY)
            )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
