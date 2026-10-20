import threading

from console_bus import ConsoleBus


def test_clear_does_not_deadlock():
    bus = ConsoleBus()
    t = threading.Thread(target=bus.clear, daemon=True)
    t.start()
    t.join(timeout=2)
    assert not t.is_alive()
