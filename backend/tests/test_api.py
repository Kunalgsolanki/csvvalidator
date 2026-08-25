from fastapi.testclient import TestClient
from app.database import PostgresConnection
from app.main import app


def test_import_validation_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.DATABASE_PATH", tmp_path / "test.db")
    with TestClient(app) as client:
        data = b"name,email,phone,company,city\nAda,ada@example.com,+14155550100,OnePrism,Delhi\n,ada@example.com,123,,Mumbai\n"
        response = client.post("/api/imports", files={"file": ("customers.csv", data, "text/csv")})
        assert response.status_code == 202
        job = response.json()
        assert job["status"] == "pending"
        job = client.get(f"/api/imports/{job['id']}").json()
        assert job["status"] == "completed"
        result = client.get(f"/api/imports/{job['id']}/records?invalid_only=true").json()
        assert result["total"] == 2
        assert any("Name is required." in item["reasons"] for item in result["items"])
        assert client.get(f"/api/imports/{job['id']}/valid-records.csv").status_code == 200
        original = client.get(f"/api/imports/{job['id']}/original.csv")
        assert original.status_code == 200
        assert original.content == data


def test_postgres_batch_insert_uses_cursor():
    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def executemany(self, query, params):
            self.query = query
            self.params = params
            return "inserted"

    class RawConnection:
        def cursor(self):
            self.created_cursor = Cursor()
            return self.created_cursor

    raw = RawConnection()
    result = PostgresConnection(raw).executemany(
        "INSERT INTO records (value) VALUES (?)", [("one",), ("two",)]
    )

    assert result == "inserted"
    assert raw.created_cursor.query == "INSERT INTO records (value) VALUES (%s)"
