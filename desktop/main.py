import json,os,tkinter as tk
from urllib.request import Request,urlopen
API=os.getenv("JARVIS_API","http://127.0.0.1:8000")
root=tk.Tk(); root.title("JARVIS"); root.geometry("700x500")
out=tk.Text(root,state="disabled"); out.pack(fill="both",expand=True,padx=10,pady=10); entry=tk.Entry(root); entry.pack(fill="x",padx=10)
def send():
 m=entry.get().strip()
 if not m:return
 entry.delete(0,"end"); out.config(state="normal"); out.insert("end","You: "+m+"\n")
 try:
  q=Request(API+"/chat",data=json.dumps({"message":m}).encode(),headers={"Content-Type":"application/json"}); ans=json.loads(urlopen(q,timeout=30).read())["response"]; out.insert("end","JARVIS: "+ans+"\n\n")
 except Exception as e: out.insert("end","JARVIS: API error: "+str(e)+"\n\n")
 out.config(state="disabled")
tk.Button(root,text="Send",command=send).pack(pady=8); entry.bind("<Return>",lambda e:send()); root.mainloop()