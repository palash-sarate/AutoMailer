import json
import unittest
from app import app
import history_manager

class BulkEmailSenderTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_config(self):
        res = self.client.get("/api/config")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("sender_email", data)
        self.assertIn("smtp_host", data)

    def test_get_files(self):
        res = self.client.get("/api/files")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("templates", data)
        self.assertIn("csv_files", data)

    def test_get_template(self):
        res = self.client.get("/api/template?file=compose.md")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("content", data)

    def test_get_csv(self):
        res = self.client.get("/api/csv?file=data.csv")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("headers", data)
        self.assertIn("rows", data)
        self.assertIn("EMAIL", data["headers"])

    def test_preview_render(self):
        res = self.client.post("/api/preview", json={
            "template": "Subject: Test for $NAME\n\nHello $NAME, invoice #$INVOICE_NO is due on $DATE for $AMOUNT.",
            "row": {
                "NAME": "John Doe",
                "INVOICE_NO": "INV-101",
                "DATE": "2026-08-20",
                "AMOUNT": "$100",
                "EMAIL": "plash.sarate28@gmail.com"
            }
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("John Doe", data["subject"])
        self.assertIn("INV-101", data["body_html"])
        self.assertIn("plash.sarate28@gmail.com", data["recipient"])

    def test_duplicate_prevention(self):
        # Record a test sent row
        row = {"NAME": "Duplicate Test", "EMAIL": "test_dup@example.com"}
        history_manager.record_send_result("test.csv", 99, "test_dup@example.com", "Test Subj", "sent", row_data=row)

        # Check that is_row_sent reports true
        is_sent, record = history_manager.is_row_sent("test.csv", 99, "test_dup@example.com", row)
        self.assertTrue(is_sent)

        # Attempt to send without force_send
        res = self.client.post("/api/send/single", json={
            "row": row,
            "template": "Hello $NAME",
            "row_index": 99,
            "csv_filename": "test.csv",
            "force_send": False
        })
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertTrue(data.get("already_sent"))

    def test_attachment_upload_and_delete(self):
        import io
        test_file = (io.BytesIO(b"Dummy attachment file content"), "test_upload.txt")
        res = self.client.post("/api/attachments/upload", data={"file": test_file}, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["attachment"]["name"], "test_upload.txt")

        # Test delete
        del_res = self.client.post("/api/attachments/delete", json={"filename": "test_upload.txt"})
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.get_json().get("success"))

if __name__ == "__main__":
    unittest.main()
