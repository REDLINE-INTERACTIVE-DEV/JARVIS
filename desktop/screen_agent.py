"""Desktop JARVIS screen bridge agent."""
from __future__ import annotations
import json, os, platform, time
from urllib.request import Request, urlopen
API=os.getenv("JARVIS_API","http://127.0.0.1:8000").rstrip("/")
DEVICE_ID=os.getenv("JARVIS_DEVICE_ID",platform.node() or "desktop")
FRAME_INTERVAL=float(os.getenv("JARVIS_SCREEN_INTERVAL","1.0"))
def request(path,method="GET",body=None,content_type="application/json"):
    req=Request(f"{API}{path}",data=body,method=method,headers={"Content-Type":content_type,"Accept":"application/json"})
    with urlopen(req,timeout=10) as response: return response.status,response.read()
def register(): request("/screen/register","POST",json.dumps({"device_id":DEVICE_ID,"platform":"desktop"}).encode())
def capture():
    import mss,mss.tools
    with mss.mss() as grabber:
        shot=grabber.grab(grabber.monitors[1]); return mss.tools.to_png(shot.rgb,shot.size)
def perform(action):
    name,args=action["action"],action.get("arguments",{})
    import pyautogui
    if name in {"click","tap"}: pyautogui.click(int(args["x"]),int(args["y"]))
    elif name=="swipe":
        pyautogui.moveTo(int(args["x1"]),int(args["y1"])); pyautogui.dragTo(int(args["x2"]),int(args["y2"]),duration=float(args.get("duration",0.25)))
    elif name=="type": pyautogui.write(str(args.get("text","")),interval=0.01)
    elif name=="hotkey": pyautogui.hotkey(*[str(x) for x in args.get("keys",[])])
    elif name=="back": pyautogui.hotkey("alt","left")
    elif name=="home" and platform.system()=="Windows": pyautogui.hotkey("win","d")
    elif name not in {"home","recents"}: raise RuntimeError(f"unsupported action: {name}")
def run():
    register()
    while True:
        try:
            request(f"/screen/frame/{DEVICE_ID}","POST",capture(),"image/png")
            _,raw=request(f"/screen/actions/{DEVICE_ID}")
            for action in json.loads(raw).get("actions",[]): perform(action)
        except Exception as exc: print(f"screen-agent: {exc}")
        time.sleep(FRAME_INTERVAL)
if __name__=="__main__": run()
