# JARVIS Screen Bridge
The bridge lets JARVIS receive the latest screen frame and queue user-authorized UI actions for a paired Android or desktop agent.
Desktop: install desktop/requirements-screen.txt, then run desktop/screen_agent.py with JARVIS_API set.
Android: enable the JARVIS accessibility service in Android settings. The service captures periodic screenshots and polls the backend for UI actions.
The bridge is device-scoped and does not silently discover or control unregistered devices.
