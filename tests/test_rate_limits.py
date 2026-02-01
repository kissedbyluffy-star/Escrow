from escrow_bot.utils.ratelimit import GlobalSpikeGuard, RateLimiter


def test_rate_limit_allows_then_blocks():
    limiter = RateLimiter()
    for _ in range(3):
        assert limiter.allow("user:1", limit=3, window_sec=60)
    assert not limiter.allow("user:1", limit=3, window_sec=60)


def test_global_spike_guard():
    guard = GlobalSpikeGuard(hard_limit=2, window_sec=10)
    assert guard.record() is True
    assert guard.record() is True
    assert guard.record() is False
