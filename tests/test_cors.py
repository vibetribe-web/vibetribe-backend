import os
import unittest


class CorsPreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
        os.environ.setdefault("SECRET_KEY", "test-secret-key")

    def test_vercel_auth_login_json_preflight_is_allowed(self) -> None:
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        response = client.options(
            "/api/v1/auth/login/json",
            headers={
                "Origin": "https://vibetribe-frontend-cyan.vercel.app",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "https://vibetribe-frontend-cyan.vercel.app",
        )
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")


if __name__ == "__main__":
    unittest.main()
