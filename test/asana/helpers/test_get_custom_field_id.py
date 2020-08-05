from src.asana import helpers as asana_helpers

from test.impl.base_test_case_class import BaseClass
from test.impl.builders.custom_field_builder import get_custom_field_settings_for_test


class TestGetCustomFieldId(BaseClass):
    @classmethod
    def setUpClass(cls):
        cls.custom_field_gid = "11111"
        cls.custom_field_name = "Test field"
        cls.custom_field_data = get_custom_field_settings_for_test(
            custom_field_gid=cls.custom_field_gid,
            custom_field_name=cls.custom_field_name,
        )

    def test_get_valid_custom_field_id(self):
        custom_field_id = asana_helpers._get_custom_field_id(
            self.custom_field_name, self.custom_field_data
        )
        self.assertEqual(custom_field_id, self.custom_field_gid)

    def test_get_invalid_custom_field_id(self):
        random_custom_field_id = asana_helpers._get_custom_field_id(
            "RandomField", self.custom_field_data
        )
        self.assertIsNone(random_custom_field_id)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
