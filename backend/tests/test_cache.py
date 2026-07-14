import pytest
from app.core.cache import CacheSerializer, cache_get, cache_set, cache_delete


class TestCacheSerializer:
    def test_serialize_dict(self):
        data = {"key": "value", "num": 42, "list": [1, 2, 3]}
        serialized = CacheSerializer.serialize(data)
        deserialized = CacheSerializer.deserialize(serialized)
        assert deserialized == data

    def test_serialize_list(self):
        data = [{"a": 1}, {"b": 2}]
        serialized = CacheSerializer.serialize(data)
        deserialized = CacheSerializer.deserialize(serialized)
        assert deserialized == data

    def test_serialize_none(self):
        result = CacheSerializer.deserialize(None)
        assert result is None

    def test_serialize_empty(self):
        data = {}
        serialized = CacheSerializer.serialize(data)
        deserialized = CacheSerializer.deserialize(serialized)
        assert deserialized == data
