import unittest


class IntentionalFailureDemo(unittest.TestCase):
    def test_required_ci_blocks_bad_change(self) -> None:
        self.fail("MS-73 intentional failure demonstration")


if __name__ == "__main__":
    unittest.main()
