#!/usr/bin/env python3
import os
import json
import subprocess

DB_FILE = "tunnels.json"
BACKHAUL_BIN = "/opt/Backhaul-manager/backhaul"
SYSTEMD_DIR = "/etc/systemd/system"

SERVER_TEMPLATE = """[server]
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

CLIENT_TEMPLATE = """[client]
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


# ---------------- STORAGE ----------------

def load():
    try:
        return json.load(open(DB_FILE))
    except:
        return []

def save(data):
    json.dump(data, open(DB_FILE, "w"), indent=2)


# ---------------- SYSTEMD ----------------

def service_name(cfg):
    return "backhaul-" + cfg.replace(".toml", "")

def service_file(name):
    return f"{SYSTEMD_DIR}/{name}.service"


def create_service(cfg):
    name = service_name(cfg)

    path = os.path.abspath(cfg)
    binpath = os.path.abspath(BACKHAUL_BIN)

    content = f"""[Unit]
Description=Backhaul {name}
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={os.getcwd()}
ExecStart={binpath} -c {path}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""

    fpath = service_file(name)
    open(fpath, "w").write(content)

    os.system("systemctl daemon-reload")
    os.system(f"systemctl enable {name}")


def delete_service(cfg):
    name = service_name(cfg)

    os.system(f"systemctl stop {name}")
    os.system(f"systemctl disable {name}")

    fpath = service_file(name)
    if os.path.exists(fpath):
        os.remove(fpath)

    os.system("systemctl daemon-reload")




TRANSPORTS={"1":"tcp","2":"tcpmux","3":"udp","4":"ws","5":"wsmux"}

def ask_default(prompt, default):
    v=input(f"{prompt} [{default}]: ").strip()
    return v if v else str(default)

def build_server_config(port, token, transport, ports, manual=False):
    cfg=f'[server]\nbind_addr = "0.0.0.0:{port}"\ntransport = "{transport}"\ntoken = "{token}"\n'
    cfg+='keepalive_period = 75\nnodelay = false\nheartbeat = 40\nchannel_size = 2048\n'
    if transport in ("tcpmux","wsmux"):
        cfg+='mux_con = 8\nmux_version = 1\nmux_framesize = 32768\nmux_recievebuffer = 4194304\nmux_streambuffer = 65536\n'
    cfg+=f'log_level = "info"\nskip_optz = true\nmss = 1360\nso_rcvbuf = 4194304\nso_sndbuf = 1048576\nports = [{ports}]\n'
    return cfg

def build_client_config(ip, port, token, transport, manual=False):
    edge=""
    if transport in ("ws","wsmux"):
        if input("Use Edge IP? (y/n): ").lower()=="y":
            edge=f'edge_ip = "{input("Edge IP: ").strip()}"\n'
    cfg=f'[client]\nremote_addr = "{ip}:{port}"\n{edge}transport = "{transport}"\ntoken = "{token}"\n'
    cfg+='connection_pool = 8\naggressive_pool = false\nkeepalive_period = 75\ndial_timeout = 10\nretry_interval = 3\nnodelay = false\n'
    if transport in ("tcpmux","wsmux"):
        cfg+='mux_version = 1\nmux_framesize = 32768\nmux_recievebuffer = 4194304\nmux_streambuffer = 65536\n'
    cfg+='log_level = "info"\nskip_optz = true\nmss = 1360\nso_rcvbuf = 1048576\nso_sndbuf = 4194304\n'
    return cfg
# ---------------- CORE ----------------

def add():
    data = load()
    mode=input("Server(s) / Client(c): ").strip().lower()
    print("\nTransport:\n1) tcp\n2) tcpmux\n3) udp\n4) ws\n5) wsmux")
    transport=TRANSPORTS.get(input("Select: ").strip(),"tcpmux")
    print("\nConfig Mode\n1) Default\n2) Manual")
    manual=input("Select: ").strip()=="2"
    port=input("Tunnel Port: ").strip()
    token=input("Token: ").strip()

    if mode in ["s","server","1"]:
        ports=input("Ports: ").strip()
        plist=",".join([f'"{x.strip()}"' for x in ports.split(",")])
        cfg=f"s-{port}.toml"
        open(cfg,"w").write(build_server_config(port,token,transport,plist,manual))
        entry={"type":"server","transport":transport,"port":port,"ports":ports,"token":token,"config":cfg}
    else:
        ip=input("Server IP: ").strip()
        cfg=f"c-{port}.toml"
        open(cfg,"w").write(build_client_config(ip,port,token,transport,manual))
        entry={"type":"client","transport":transport,"port":port,"token":token,"server_ip":ip,"config":cfg}

    data.append(entry)
    save(data)
    create_service(cfg)
    if input("Start now? (y/n): ").lower()=="y":
        os.system(f"systemctl start {service_name(cfg)}")

def listt():
    for i, t in enumerate(load(), 1):
        print(f"{i}. {t['config']} | {t['type']} | {t['port']}")


def delete():
    data = load()
    listt()

    try:
        i = int(input("Select: ")) - 1
    except:
        return

    if i < 0 or i >= len(data):
        return

    cfg = data[i]["config"]

    delete_service(cfg)

    if os.path.exists(cfg):
        os.remove(cfg)

    data.pop(i)
    save(data)


def start_one():
    listt()
    i = int(input("Select: ")) - 1
    cfg = load()[i]["config"]
    os.system(f"systemctl start {service_name(cfg)}")


def stop_one():
    listt()
    i = int(input("Select: ")) - 1
    cfg = load()[i]["config"]
    os.system(f"systemctl stop {service_name(cfg)}")


def restart_one():
    listt()
    i = int(input("Select: ")) - 1
    cfg = load()[i]["config"]
    name = service_name(cfg)
    os.system(f"systemctl restart {name}")


def status():
    for t in load():
        name = service_name(t["config"])
        out = os.system(f"systemctl is-active --quiet {name}")
        st = "Running" if out == 0 else "Stopped"
        print(f"{t['config']:20} {st}")


def logs():
    listt()
    i = int(input("Select: ")) - 1
    cfg = load()[i]["config"]
    name = service_name(cfg)
    os.system(f"journalctl -u {name} -f")


def all_start():
    for t in load():
        os.system(f"systemctl start {service_name(t['config'])}")


def all_stop():
    for t in load():
        os.system(f"systemctl stop {service_name(t['config'])}")


def all_restart():
    all_stop()
    all_start()


# ===== Added by upgrade =====

def clone_tunnel():
    data = load()
    listt()
    try:
        i = int(input("Select tunnel to clone: ")) - 1
    except:
        return
    if i < 0 or i >= len(data):
        return

    t = data[i].copy()
    new_port = input("New Tunnel Port: ").strip()

    old_cfg = t["config"]
    new_cfg = ("s-" if t["type"]=="server" else "c-") + new_port + ".toml"

    txt = open(old_cfg).read()
    txt = txt.replace(f':{t["port"]}"', f':{new_port}"')
    open(new_cfg,"w").write(txt)

    t["port"] = new_port
    t["config"] = new_cfg

    data.append(t)
    save(data)

    try:
        create_service(new_cfg)
    except:
        pass

    print("Tunnel cloned.")


def reconfigure_tunnel():
    data = load()

    if not data:
        print("No tunnels found.")
        return

    listt()

    try:
        idx = int(input("Select tunnel: ")) - 1
    except:
        return

    if idx < 0 or idx >= len(data):
        return

    t = data[idx]

    cfg = t["config"]

    print("\nLeave empty to keep current value\n")

    # Stop service
    try:
        os.system(f"systemctl stop {service_name(cfg)}")
    except:
        pass

    # Transport
    print("\nTransport:")
    print("1) tcp")
    print("2) tcpmux")
    print("3) udp")
    print("4) ws")
    print("5) wsmux")

    transport_map = {
        "1": "tcp",
        "2": "tcpmux",
        "3": "udp",
        "4": "ws",
        "5": "wsmux"
    }

    current_transport = t.get("transport", "tcpmux")

    transport_input = input(
        f"Transport [{current_transport}]: "
    ).strip()

    if transport_input in transport_map:
        transport = transport_map[transport_input]
    elif transport_input:
        transport = transport_input
    else:
        transport = current_transport

    # Token
    token = input(
        f'Token [{t.get("token","")}]: '
    ).strip() or t.get("token","")

    # SERVER
    if t["type"] == "server":

        current_ports = t.get("ports", "")

        ports = input(
            f'Ports [{current_ports}]: '
        ).strip() or current_ports

        plist = ",".join(
            [f'"{x.strip()}"' for x in ports.split(",") if x.strip()]
        )

        cfg_text = build_server_config(
            t["port"],
            token,
            transport,
            plist,
            False
        )

        with open(cfg, "w") as f:
            f.write(cfg_text)

        t["ports"] = ports

    # CLIENT
    else:

        ip = input(
            f'Server IP [{t.get("server_ip","")}]: '
        ).strip() or t.get("server_ip","")

        cfg_text = build_client_config(
            ip,
            t["port"],
            token,
            transport,
            False
        )

        with open(cfg, "w") as f:
            f.write(cfg_text)

        t["server_ip"] = ip

    # Update json
    t["transport"] = transport
    t["token"] = token

    data[idx] = t
    save(data)

    # Restart service
    try:
        os.system(f"systemctl restart {service_name(cfg)}")
    except:
        pass

    print("\nTunnel updated successfully.")

# ---------------- MENU ----------------

while True:
    os.system("clear")
    print("""
BACKHAUL MANAGER (SYSTEMD)

1 Add Tunnel
2 Delete Tunnel
3 List Tunnels
4 Start Tunnel
5 Stop Tunnel
6 Restart Tunnel
7 Start All
8 Stop All
9 Restart All
10 Status
11 Logs
12 Reconfigure Tunnel

14 Exit
""")

    c = input("Select: ")

    if c == "1":
        add()
    elif c == "2":
        delete()
    elif c == "3":
        listt()
    elif c == "4":
        start_one()
    elif c == "5":
        stop_one()
    elif c == "6":
        restart_one()
    elif c == "7":
        all_start()
    elif c == "8":
        all_stop()
    elif c == "9":
        all_restart()
    elif c == "10":
        status()
    elif c == "11":
        logs()
    elif c == "12":
      reconfigure_tunnel()
    # elif c == "13":
    #   clone_tunnel()
    elif c == "14":
        break

    input("\nEnter...")
