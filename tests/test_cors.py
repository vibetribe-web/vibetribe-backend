import os
import unittest


class CorsPreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
        os.environ.setdefault("SECRET_KEY", "test-secret-key")

    def test_auth_preflights_are_allowed_for_frontend_origins(self) -> None:
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "https://vibetribe.vercel.app",
            "https://vibetribe-two.vercel.app",
            "https://vibetribe-git-main-vibetribe.vercel.app",
        ]

        for origin in allowed_origins:
            with self.subTest(origin=origin):
                response = client.options(
                    "/api/v1/auth/login/json",
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "content-type,authorization",
                    },
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
                self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")


if __name__ == "__main__":
    unittest.main()
