import os
from pathlib import Path
class LocalBrain:
 def __init__(self):
  self.model_path=os.getenv("JARVIS_MODEL_PATH"); self._llm=None
  if self.model_path and Path(self.model_path).exists():
   try:
    from llama_cpp import Llama
    self._llm=Llama(model_path=self.model_path,n_ctx=int(os.getenv("JARVIS_CTX","4096")),verbose=False)
   except Exception: self._llm=None
 def respond(self,message,memories):
  if self._llm:
   context="\n".join(m["kind"]+": "+m["content"] for m in reversed(memories[-8:]))
   prompt="You are JARVIS, a concise local personal assistant.\nMemory:\n"+context+"\nUser: "+message+"\nJARVIS:"
   return self._llm(prompt,max_tokens=512,stop=["\nUser:"])["choices"][0]["text"].strip()
  return "Local foundation mode is active. You said: "+message