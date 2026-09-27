from backend.app.robots.safety import can_dispatch,validate_capabilities

def test_safe_capabilities():
    assert validate_capabilities(["telemetry","camera","navigation"])==["camera","navigation","telemetry"]

def test_invalid_capability():
    try: validate_capabilities(["unknown"])
    except ValueError: return
    assert False

def test_dispatch_requires_healthy_connection():
    assert can_dispatch({"connected":True,"healthy":True,"emergency_stop":False})
    assert not can_dispatch({"connected":False,"healthy":True,"emergency_stop":False})
    assert not can_dispatch({"connected":True,"healthy":False,"emergency_stop":False})
    assert not can_dispatch({"connected":True,"healthy":True,"emergency_stop":True})
