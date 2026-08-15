import json
import os
import unittest
from app import app
import history_manager

class BulkEmailSenderTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        if not os.path.exists("compose.md"):
            with open("compose.md", "w", encoding="utf-8") as f:
                f.write("Invoice Reminder for $NAME - $DATE\n\nHello $NAME\n")
        if not os.path.exists("data.csv"):
            with open("data.csv", "w", encoding="utf-8") as f:
                f.write("NAME,DATE,AMOUNT,INVOICE_NO,EMAIL\nJohn Doe,2026-08-20,$250.00,INV-1001,test@example.com\n")

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

    def test_template_upload(self):
        import io
        test_tpl = (io.BytesIO(b"# Hello $NAME\n\nUploaded template body"), "uploaded_test.md")
        res = self.client.post("/api/template/upload", data={"file": test_tpl}, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("file"), "uploaded_test.md")
        self.assertIn("Hello $NAME", data.get("content", ""))
        if os.path.exists("uploaded_test.md"):
            os.remove("uploaded_test.md")

    def test_csv_upload(self):
        import io
        test_csv = (io.BytesIO(b"NAME,EMAIL,INVOICE\nAlice,alice@example.com,INV-99\n"), "uploaded_test.csv")
        res = self.client.post("/api/csv/upload", data={"file": test_csv}, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("file"), "uploaded_test.csv")
        self.assertIn("INVOICE", data.get("headers", []))
        self.assertEqual(len(data.get("rows", [])), 1)
        if os.path.exists("uploaded_test.csv"):
            os.remove("uploaded_test.csv")

    def test_cc_bcc_preview_and_parsing(self):
        import mailer_service
        # Test parse_email_list
        emails = mailer_service.parse_email_list("a@b.com, c@d.com; manager@test.com, $BOSS", {"BOSS": "boss@test.com"})
        self.assertIn("a@b.com", emails)
        self.assertIn("c@d.com", emails)
        self.assertIn("manager@test.com", emails)
        self.assertIn("boss@test.com", emails)

        # Test preview with CC and BCC
        res = self.client.post("/api/preview", json={
            "template": "Subject: Test\n\nBody",
            "row": {
                "EMAIL": "recipient@test.com",
                "CC": "row_cc@test.com",
                "BCC": "row_bcc@test.com"
            }
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("cc", data)
        self.assertIn("bcc", data)
        self.assertIn("row_cc@test.com", data["cc"])
        self.assertIn("row_bcc@test.com", data["bcc"])

    def test_batch_stop_endpoint(self):
        res = self.client.post("/api/send/batch-stop", json={"batch_id": "test_batch_123"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))

    def test_semver_parsing_and_comparison(self):
        import updater_service
        self.assertEqual(updater_service.parse_semver("v1.0.1"), (1, 0, 1))
        self.assertEqual(updater_service.parse_semver("1.2.3"), (1, 2, 3))
        self.assertEqual(updater_service.parse_semver("v2.0.0-beta"), (2, 0, 0))

        self.assertTrue(updater_service.is_newer_version("v1.0.2", "v1.0.1"))
        self.assertTrue(updater_service.is_newer_version("v1.1.0", "v1.0.9"))
        self.assertTrue(updater_service.is_newer_version("v2.0.0", "v1.99.99"))
        self.assertFalse(updater_service.is_newer_version("v1.0.1", "v1.0.1"))
        self.assertFalse(updater_service.is_newer_version("v1.0.0", "v1.0.1"))

    def test_version_status_endpoint(self):
        res = self.client.get("/api/version/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("version", data)
        self.assertIn("is_frozen", data)
        self.assertIn("repo", data)
        self.assertEqual(data["version"], "1.0.1")

if __name__ == "__main__":
    unittest.main()
