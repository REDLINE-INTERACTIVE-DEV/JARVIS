DESTRUCTIVE={"delete_file","shutdown","restart","kill_process","send_message","purchase"}
class ToolRegistry:
 def call(self,name,arguments,confirmed=False):
  if name!="computer": return {"ok":False,"confirmation_required":False,"output":"Unknown tool: "+name}
  action=arguments.get("action","")
  if action in DESTRUCTIVE and not confirmed: return {"ok":False,"confirmation_required":True,"output":"Confirmation required for destructive action: "+action}
  if action in DESTRUCTIVE: return {"ok":False,"confirmation_required":False,"output":"Destructive action is gated; no OS executor is installed yet"}
  return {"ok":True,"confirmation_required":False,"output":"Safe computer action accepted: "+action}