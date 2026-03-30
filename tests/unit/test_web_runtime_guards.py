from abliterador_web.app import ModelsCache, SlidingWindowRateLimiter
from abliterador_web.network import is_local_network_ip


def test_is_local_network_ip_flags_private_and_loopback():
    assert is_local_network_ip("127.0.0.1") is True
    assert is_local_network_ip("192.168.1.50") is True
    assert is_local_network_ip("8.8.8.8") is False


def test_rate_limiter_blocks_when_limit_exceeded():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_s=60)
    assert limiter.allow("1.1.1.1") is True
    assert limiter.allow("1.1.1.1") is True
    assert limiter.allow("1.1.1.1") is False


def test_models_cache_reuses_loader_until_ttl():
    calls = {"count": 0}

    def loader():
        calls["count"] += 1
        return ["model-a"]

    cache = ModelsCache(ttl_s=999)
    first = cache.get_or_load(loader)
    second = cache.get_or_load(loader)

    assert first == ["model-a"]
    assert second == ["model-a"]
    assert calls["count"] == 1
