import unittest

from scripts.check_build_version import check_reservation, patch_number


class BuildVersionTests(unittest.TestCase):
    def test_new_and_exact_retry(self):
        check_reservation("0.3.3.5", "a", [])
        check_reservation("0.3.3.5", "a", [(602, "a", "0.3.3.5")])
        check_reservation("0.3.3.6", "b", [(602, "a", "0.3.3.5")])

    def test_reused_version_rejected_even_after_failed_attempt(self):
        history = [(602, "a", "0.3.3.5"), (603, "b", "0.3.3.5")]
        with self.assertRaises(ValueError):
            check_reservation("0.3.3.5", "b", history)
        check_reservation("0.3.3.5", "a", history)

    def test_higher_reserved_number_and_out_of_order_attempt(self):
        history = [(602, "a", "0.3.3.5"), (603, "c", "0.3.3.7"),
                   (604, "b", "0.3.3.6")]
        with self.assertRaises(ValueError):
            check_reservation("0.3.3.6", "b", history)
        check_reservation("0.3.3.8", "d", history)
        check_reservation("0.3.3.5", "a", history)

    def test_legacy_and_invalid_numbers(self):
        for version in ("0.3.3.4", "0.3.3", "0.3.3.05", "0.3.3.5-preview"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                check_reservation(version, "a", [])
        self.assertEqual(patch_number("0.3.3.10"), 10)
