from src.asana import helpers as asana_helpers

from test.impl.base_test_case_class import BaseClass
from test.impl.builders.custom_field_builder import get_custom_field_settings_for_test


class TestGetCustomFieldValue(BaseClass):
    @classmethod
    def setUpClass(cls):
        cls.custom_field_gid = "11111"
        cls.custom_field_name = "Test field"
        cls.enabled_enum_option_gid = "22222"
        cls.enabled_enum_option_name = "enabled"
        cls.disabled_enum_option_gid = "33333"
        cls.disabled_enum_option_name = "disabled"
        cls.custom_field_data = get_custom_field_settings_for_test(
            custom_field_gid=cls.custom_field_gid,
            custom_field_name=cls.custom_field_name,
            enabled_enum_option_gid=cls.enabled_enum_option_gid,
            enabled_enum_option_name=cls.enabled_enum_option_name,
            disabled_enum_option_gid=cls.disabled_enum_option_gid,
            disabled_enum_option_name=cls.enabled_enum_option_name,
        )

    def test_get_valid_people_custom_field_value(self):
        cf_name = "Author"
        expected_cf_value = "9999999999"
        custom_field_data = [{
            "gid": "1243324",
            "custom_field": {
                "name": cf_name,
                "resource_type": "custom_field",
                "resource_subtype": "people",
            },
            "resource_type": "custom_field_setting",
        }]
        cf_value = asana_helpers._get_custom_field_value(
            cf_name,
            expected_cf_value,
            custom_field_data,
        )
        self.assertEqual(cf_value, expected_cf_value)


    def test_get_valid_custom_field_enum_option_id(self):
        enum_option_id = asana_helpers._get_custom_field_value(
            self.custom_field_name,
            self.enabled_enum_option_name,
            self.custom_field_data,
        )
        self.assertEqual(enum_option_id, self.enabled_enum_option_gid)

    def test_invalid_custom_field(self):
        enum_option_id = asana_helpers._get_custom_field_value(
            "RandomField", self.enabled_enum_option_name, self.custom_field_data
        )
        self.assertIsNone(enum_option_id)

    def test_invalid_enum_option(self):
        enum_option_id = asana_helpers._get_custom_field_value(
            self.custom_field_name, "RandomEnumOption", self.custom_field_data
        )
        self.assertIsNone(enum_option_id)

    def test_get_enum_option_id_for_disabled_option(self):
        enum_option_id = asana_helpers._get_custom_field_value(
            self.custom_field_name,
            self.disabled_enum_option_name,
            self.custom_field_data,
        )
        self.assertIsNone(enum_option_id)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
