from pathlib import Path
p=Path('backend/tests/test_api.py')
s=p.read_text()
s=s.replace('assert memories[0]["kind"] == "assistant"','assert memories[0]["kind"].startswith("assistant:")')
p.write_text(s)
