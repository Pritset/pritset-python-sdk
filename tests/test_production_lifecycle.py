import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from production_lifecycle import _document_data


class ProductionLifecycleTest(unittest.TestCase):
    def test_document_data_matches_the_staging_template_shape(self) -> None:
        data = _document_data("abc123")

        self.assertEqual(data["title"], "Pritset SDK production test-user validation")
        self.assertEqual(data["description"], "Lifecycle run abc123")
        self.assertEqual(
            data["advantages"],
            [
                {
                    "title": "Contract",
                    "description": "All public template operations completed.",
                },
                {
                    "title": "Cleanup",
                    "description": "The temporary template is deleted after validation.",
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
