from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_redirects_to_contacts():
    response = client.get("/", allow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/contacts"
