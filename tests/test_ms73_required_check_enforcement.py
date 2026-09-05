import unittest


class RequiredCheckEnforcementDemo(unittest.TestCase):
    def test_required_ci_blocks_bad_change(self) -> None:
        self.fail("MS-73 intentional branch-protection failure demonstration")


if __name__ == "__main__":
    unittest.main()
