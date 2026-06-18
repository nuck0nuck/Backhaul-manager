#!/usr/bin/env python3
import os, json, signal, subprocess, threading, time

DB_FILE="tunnels.json"
PID_FILE="pids.json"
BACKHAUL_BIN="./backhaul"

SERVER_TEMPLATE="""[server]
bind_addr = "0.0.0.0:{port}"
transport = "tcpmux"
token = "{token}"
keepalive_period = 75
nodelay = true
heartbeat = 40
channel_size = 2048
mux_con = 8
mux_version = 1
mux_framesize = 32768
mux_recievebuffer = 4194304
mux_streambuffer = 65536
log_level = "info"
ports = [{ports}]
"""

CLIENT_TEMPLATE="""[client]
remote_addr = "{ip}:{port}"
transport = "tcpmux"
token = "{token}"
connection_pool = 8
aggressive_pool = false
keepalive_period = 75
dial_timeout = 10
retry_interval = 3
nodelay = true
mux_version = 1
mux_framesize = 32768
mux_recievebuffer = 4194304
mux_streambuffer = 65536
log_level = "info"
"""

def loadj(f,d):
    try:
        return json.load(open(f))
    except:
        return d

def savej(f,d):
    json.dump(d,open(f,"w"),indent=2)

def tunnels(): return loadj(DB_FILE,[])
def pids(): return loadj(PID_FILE,{})

def save_pids(x): savej(PID_FILE,x)

def alive(pid):
    try:
        os.kill(int(pid),0)
        return True
    except:
        return False

def start_cfg(cfg):
    pd=pids()
    if cfg in pd and alive(pd[cfg]): return
    log=open(cfg+".log","a")
    p=subprocess.Popen([BACKHAUL_BIN,"-c",cfg],stdout=log,stderr=log,start_new_session=True)
    pd[cfg]=p.pid
    save_pids(pd)

def stop_cfg(cfg):
    pd=pids()
    if cfg in pd:
        try: os.kill(int(pd[cfg]),signal.SIGTERM)
        except: pass
        pd.pop(cfg,None)
        save_pids(pd)

def watchdog():
    while True:
        for t in tunnels():
            cfg=t["config"]
            if t.get("autostart",False):
                pd=pids()
                if cfg not in pd or not alive(pd[cfg]):
                    start_cfg(cfg)
        time.sleep(30)

def add():
    ts=tunnels()
    m=input("Server(s) / Client(c): ").strip().lower()
    port=input("Tunnel Port: ").strip()
    token=input("Token: ").strip()
    if not token: return
    if m in ("s","server","1"):
        ports=input("Ports: ").strip()
        plist=",".join([f'"{x.strip()}"' for x in ports.split(",")])
        cfg=f"s-{port}.toml"
        open(cfg,"w").write(SERVER_TEMPLATE.format(port=port,token=token,ports=plist))
        ts.append({"type":"server","port":port,"token":token,"config":cfg,"autostart":True})
    else:
        ip=input("Server IP: ").strip()
        cfg=f"c-{port}.toml"
        open(cfg,"w").write(CLIENT_TEMPLATE.format(ip=ip,port=port,token=token))
        ts.append({"type":"client","port":port,"token":token,"server_ip":ip,"config":cfg,"autostart":True})
    savej(DB_FILE,ts)
    if input("Start now? y/n: ").lower()=="y":
        start_cfg(cfg)

def listt():
    for i,t in enumerate(tunnels(),1):
        print(i,t["config"],t["type"],"port",t["port"])

def delete():
    ts=tunnels()
    listt()
    try:i=int(input("Select: "))-1
    except:return
    if not(0<=i<len(ts)): return
    cfg=ts[i]["config"]
    stop_cfg(cfg)
    for f in [cfg,cfg+".log"]:
        if os.path.exists(f): os.remove(f)
    ts.pop(i)
    savej(DB_FILE,ts)

def start_one():
    listt(); i=int(input("Select: "))-1
    start_cfg(tunnels()[i]["config"])

def stop_one():
    listt(); i=int(input("Select: "))-1
    stop_cfg(tunnels()[i]["config"])

def logs():
    listt(); i=int(input("Select: "))-1
    cfg=tunnels()[i]["config"]
    os.system(f"tail -n 50 {cfg}.log")

def status():
    pd=pids()
    for t in tunnels():
        cfg=t["config"]
        st="Running" if cfg in pd and alive(pd[cfg]) else "Stopped"
        print(f"{cfg:20} {st}")

threading.Thread(target=watchdog,daemon=True).start()

while True:
    os.system("clear")
    print("""
1 Add Tunnel
2 Delete Tunnel
3 List Tunnels
4 Start Tunnel
5 Stop Tunnel
6 Start All
7 Stop All
8 Restart All
9 Status
10 View Logs
11 Exit
""")
    c=input("Select: ")
    if c=="1": add()
    elif c=="2": delete()
    elif c=="3": listt()
    elif c=="4": start_one()
    elif c=="5": stop_one()
    elif c=="6":
        [start_cfg(t["config"]) for t in tunnels()]
    elif c=="7":
        [stop_cfg(t["config"]) for t in tunnels()]
    elif c=="8":
        [stop_cfg(t["config"]) for t in tunnels()]
        time.sleep(1)
        [start_cfg(t["config"]) for t in tunnels()]
    elif c=="9": status()
    elif c=="10": logs()
    elif c=="11": break
    input("\\nEnter...")
