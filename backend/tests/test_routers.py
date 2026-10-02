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


    def test_sample_loader_routes_registered(self):
        """Verify 1-click sample document loader and list endpoints."""
        routes = [r.path for r in doc_router.routes]
        self.assertIn("/tender/sample", routes)
        self.assertIn("/sample/vendor-bids", routes)
        self.assertIn("/sample/load/{sample_name}", routes)
        self.assertIn("/list", routes)

if __name__ == '__main__':
    unittest.main()



from routers.audit import router as audit_router

class TestAuditRouter(unittest.TestCase):
    def test_audit_router_routes_registered(self):
        """Verify audit run, clause override, status polling and PDF download routes."""
        routes = [r.path for r in audit_router.routes]
        self.assertIn("/run", routes)
        self.assertIn("/clause-override", routes)
        self.assertIn("/status/{audit_id}", routes)
        self.assertIn("/report/pdf/{audit_id}", routes)
