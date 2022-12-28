from typing import List, Dict


def get_enum_custom_field_setting_for_test(
    custom_field_gid: str = "12345",
    custom_field_name: str = "test",
    enabled_enum_option_gid: str = "67890",
    enabled_enum_option_name: str = "enabled option",
    disabled_enum_option_gid: str = "67890",
    disabled_enum_option_name: str = "disabled option",
) -> Dict:
    return {
                "gid": custom_field_gid,
                "enum_options": [
                    {
                        "gid": enabled_enum_option_gid,
                        "color": "green",
                        "enabled": True,
                        "name": enabled_enum_option_name,
                        "resource_type": "enum_option",
                    },
                    {
                        "gid": disabled_enum_option_gid,
                        "color": "red",
                        "enabled": False,
                        "name": disabled_enum_option_name,
                        "resource_type": "enum_option",
                    },
                ],
                "name": custom_field_name,
                "resource_subtype": "enum",
                "resource_type": "custom_field",
                "type": "enum",
        }
