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


# ---------------- CORE ----------------

def add():
    data = load()

    mode = input("Server(s) / Client(c): ").strip().lower()
    port = input("Tunnel Port: ").strip()
    token = input("Token: ").strip()

    if not token:
        print("Token required")
        return

    if mode in ["s", "server", "1"]:
        ports = input("Ports (example: 45093,45094=45093): ").strip()
        plist = ",".join([f'"{x.strip()}"' for x in ports.split(",")])

        cfg = f"s-{port}.toml"
        open(cfg, "w").write(SERVER_TEMPLATE.format(
            port=port, token=token, ports=plist
        ))

        entry = {
            "type": "server",
            "port": port,
            "token": token,
            "config": cfg
        }

    else:
        ip = input("Server IP: ").strip()

        cfg = f"c-{port}.toml"
        open(cfg, "w").write(CLIENT_TEMPLATE.format(
            ip=ip, port=port, token=token
        ))

        entry = {
            "type": "client",
            "port": port,
            "token": token,
            "server_ip": ip,
            "config": cfg
        }

    data.append(entry)
    save(data)

    # systemd service
    create_service(cfg)

    if input("Start now? (y/n): ").lower() == "y":
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
12 Exit
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
        break

    input("\nEnter...")
