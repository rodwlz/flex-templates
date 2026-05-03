"""
Adapter tests. Redis uses fakeredis; file adapter uses tmp_path.
"""
import pytest
import json
import csv
from pathlib import Path
from lib.adapters.redis_adapter import RedisAdapter
from lib.adapters.file_adapter import FileAdapter
from lib.contracts.base import ActionRequest


@pytest.fixture
def redis_adapter():
    import fakeredis
    adapter = RedisAdapter(host="localhost")
    adapter._r = fakeredis.FakeRedis(decode_responses=True)
    return adapter


def test_redis_set_get(redis_adapter):
    result = redis_adapter.execute(ActionRequest(
        action="set",
        data={"key": "user:1", "value": "alice"}
    ))
    assert result.success
    assert result.data["stored"] is True

    result = redis_adapter.execute(ActionRequest(
        action="get",
        data={"key": "user:1"}
    ))
    assert result.success
    assert result.data["value"] == "alice"
    assert result.data["found"] is True


def test_redis_delete(redis_adapter):
    redis_adapter.execute(ActionRequest(action="set", data={"key": "k1", "value": "v1"}))
    result = redis_adapter.execute(ActionRequest(action="delete", data={"key": "k1"}))
    assert result.success
    assert result.data["deleted"] is True

    result = redis_adapter.execute(ActionRequest(action="get", data={"key": "k1"}))
    assert result.data["found"] is False


def test_redis_exists(redis_adapter):
    redis_adapter.execute(ActionRequest(action="set", data={"key": "exists_key", "value": "yes"}))
    result = redis_adapter.execute(ActionRequest(action="exists", data={"key": "exists_key"}))
    assert result.data["exists"] is True

    result = redis_adapter.execute(ActionRequest(action="exists", data={"key": "nope"}))
    assert result.data["exists"] is False


def test_redis_keys_pattern(redis_adapter):
    redis_adapter.execute(ActionRequest(action="set", data={"key": "user:1", "value": "a"}))
    redis_adapter.execute(ActionRequest(action="set", data={"key": "user:2", "value": "b"}))
    redis_adapter.execute(ActionRequest(action="set", data={"key": "post:1", "value": "c"}))

    result = redis_adapter.execute(ActionRequest(action="keys", data={"pattern": "user:*"}))
    assert "user:1" in result.data["keys"]
    assert "user:2" in result.data["keys"]
    assert "post:1" not in result.data["keys"]


@pytest.fixture
def file_adapter(tmp_path):
    return FileAdapter(base_path=str(tmp_path))


def test_file_read_csv(file_adapter, tmp_path):
    csv_file = tmp_path / "data.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "age"])
        writer.writerow(["alice", "30"])
        writer.writerow(["bob", "25"])

    result = file_adapter.execute(ActionRequest(
        action="read",
        data={"path": "data.csv"}
    ))
    assert result.success
    assert len(result.data["rows"]) == 2
    assert result.data["rows"][0]["name"] == "alice"
    assert result.data["count"] == 2


def test_file_read_json(file_adapter, tmp_path):
    json_file = tmp_path / "data.json"
    json_file.write_text(json.dumps([{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}]))

    result = file_adapter.execute(ActionRequest(
        action="read",
        data={"path": "data.json"}
    ))
    assert result.success
    assert len(result.data["rows"]) == 2
    assert result.data["rows"][0]["name"] == "alice"


def test_file_read_with_limit(file_adapter, tmp_path):
    csv_file = tmp_path / "big.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["x"])
        for i in range(10):
            writer.writerow([str(i)])

    result = file_adapter.execute(ActionRequest(
        action="read",
        data={"path": "big.csv", "limit": 3}
    ))
    assert len(result.data["rows"]) == 3


def test_file_read_with_columns(file_adapter, tmp_path):
    csv_file = tmp_path / "cols.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "age", "city"])
        writer.writerow(["alice", "30", "NYC"])
        writer.writerow(["bob", "25", "LA"])

    result = file_adapter.execute(ActionRequest(
        action="read",
        data={"path": "cols.csv", "columns": ["name", "age"]}
    ))
    assert "name" in result.data["rows"][0]
    assert "age" in result.data["rows"][0]
    assert "city" not in result.data["rows"][0]


def test_file_list(file_adapter, tmp_path):
    (tmp_path / "a.csv").touch()
    (tmp_path / "b.json").touch()
    (tmp_path / "c.txt").touch()

    result = file_adapter.execute(ActionRequest(action="list", data={}))
    assert "a.csv" in result.data["files"]
    assert "b.json" in result.data["files"]
    assert "c.txt" not in result.data["files"]


def test_file_path_traversal_blocked(file_adapter):
    result = file_adapter.execute(ActionRequest(
        action="read",
        data={"path": "../../etc/passwd"}
    ))
    assert not result.success
    assert "traversal" in result.error.lower()


def test_file_unsupported_format(file_adapter, tmp_path):
    txt_file = tmp_path / "data.txt"
    txt_file.write_text("hello")

    result = file_adapter.execute(ActionRequest(
        action="read",
        data={"path": "data.txt"}
    ))
    assert not result.success
    assert "unsupported" in result.error.lower()
