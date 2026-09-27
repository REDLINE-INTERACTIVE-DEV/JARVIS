from backend.app.sync import IncrementalSync, SyncEvent

def test_gmail_sync_preserves_identity_and_version():
    item=SyncEvent("gmail","account-a","message-123","history-456","email","Build update","APK completed")
    event=IncrementalSync("gmail").to_event("phone",item)
    assert event["external_id"]=="message-123"
    assert event["version"]=="history-456"

def test_sync_rejects_wrong_provider():
    try: IncrementalSync("gmail").to_event("desktop",SyncEvent("github","a","1","1","activity","title","body"))
    except ValueError: return
    raise AssertionError("wrong provider must be rejected")
