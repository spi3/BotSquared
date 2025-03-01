import unittest

from bot_squared.plugins.template import Template


class TestTemplate(unittest.TestCase):
    def test_create(self):
        self.assertIsInstance(Template(), Template)


if __name__ == '__main__':
    unittest.main()
