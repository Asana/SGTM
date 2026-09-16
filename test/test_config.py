import os
from unittest.mock import patch

from test.impl.base_test_case_class import BaseClass


class TestOptionalIntEnv(BaseClass):
    def test_malformed_values_fall_back_to_the_default(self):
        import src.config as config

        with patch.dict(os.environ, {"SOME_INT": "1.5"}):
            self.assertEqual(config._optional_int_env("SOME_INT", 1), 1)
        with patch.dict(os.environ, {"SOME_INT": "3"}):
            self.assertEqual(config._optional_int_env("SOME_INT", 1), 3)
        with patch.dict(os.environ, {"SOME_INT": ""}):
            self.assertEqual(config._optional_int_env("SOME_INT", 2), 2)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
