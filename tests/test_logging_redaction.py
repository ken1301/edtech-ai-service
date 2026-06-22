import unittest

from infrastructure.logging import KEY_REDACTED, REDACTED, URL_REDACTED, redact_event_dict


class LoggingRedactionTests(unittest.TestCase):
    def test_redacts_sensitive_fields_by_name(self):
        event_dict = {
            "authorization": "Bearer secret-token",
            "x_api_key": "api-key-value",
            "system_prompt": "full prompt content",
            "user_msg": "student free text",
            "final_answer": "42",
            "response_content": "assistant reply",
        }

        redacted = redact_event_dict(None, "info", event_dict)

        self.assertEqual(redacted["authorization"], REDACTED)
        self.assertEqual(redacted["x_api_key"], REDACTED)
        self.assertEqual(redacted["system_prompt"], REDACTED)
        self.assertEqual(redacted["user_msg"], REDACTED)
        self.assertEqual(redacted["final_answer"], REDACTED)
        self.assertEqual(redacted["response_content"], REDACTED)

    def test_redacts_document_urls_and_object_keys_in_nested_structures(self):
        event_dict = {
            "document_url": "https://bucket.example/users/user-1/pdfs/doc-1/file.pdf?X-Amz-Signature=abc",
            "payload": {
                "messages": [
                    {"content": "student free text"},
                    {"attachment_url": "https://bucket.example/users/user-1/images/img-1/file.png"},
                ],
                "object_key": "users/user-1/pdfs/doc-1/file.pdf",
            },
            "error": "Failed to fetch https://bucket.example/users/user-1/pdfs/doc-1/file.pdf?token=abc",
        }

        redacted = redact_event_dict(None, "info", event_dict)

        self.assertEqual(redacted["document_url"], URL_REDACTED)
        self.assertEqual(redacted["payload"]["messages"], REDACTED)
        self.assertEqual(redacted["payload"]["object_key"], KEY_REDACTED)
        self.assertEqual(redacted["error"], URL_REDACTED)

    def test_leaves_non_sensitive_fields_intact(self):
        event_dict = {
            "event": "create_lesson2.completed",
            "user_id": "user-1",
            "status_code": 200,
            "model": "gpt-5.4-mini",
            "correlation_id": "corr-1",
        }

        redacted = redact_event_dict(None, "info", event_dict)

        self.assertEqual(redacted, event_dict)


if __name__ == "__main__":
    unittest.main()