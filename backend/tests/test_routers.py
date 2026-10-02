import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from routers.document import router as doc_router, ALLOWED_EXTENSIONS

class TestDocumentRouter(unittest.TestCase):
    def test_router_routes_registered(self):
        """Verify document upload and tender upload routes are mounted."""
        routes = [r.path for r in doc_router.routes]
        self.assertIn("/upload", routes)
        self.assertIn("/tender/upload", routes)

    def test_allowed_extensions_whitelist(self):
        """Verify standard government bid file extensions are whitelisted."""
        self.assertIn(".pdf", ALLOWED_EXTENSIONS)
        self.assertIn(".docx", ALLOWED_EXTENSIONS)
        self.assertIn(".xlsx", ALLOWED_EXTENSIONS)
        self.assertIn(".png", ALLOWED_EXTENSIONS)

if __name__ == '__main__':
    unittest.main()
