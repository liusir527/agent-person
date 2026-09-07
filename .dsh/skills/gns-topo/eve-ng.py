#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EVE-NG Topology Automation Script using evengsdk
Read topology from YAML and auto-deploy to EVE-NG server

⚠️ This script MUST use evengsdk exclusively. Do NOT use requests to call
EVE-NG API directly — evengsdk handles authentication, session management,
and interface name resolution correctly.
"""

import yaml
import argparse
import sys
import time

# === Pre-flight check: evengsdk is mandatory ===
try:
    from evengsdk.client import EvengClient
except ImportError:
    print("[ERROR] evengsdk is NOT installed. EVE-NG deployment requires evengsdk.")
    print("        Do NOT fall back to requests — install evengsdk first:")
    print("        pip install evengsdk")
    sys.exit(1)

# Template name mapping: YAML template name -> EVE-NG template key
TEMPLATE_MAP = {
    "NF605":            "nsfocusnf",
    "huawei-ce6800":    "huaweice6800",
    "linux-ubuntu22.04": "linux",
}

# Icon mapping: YAML icon (GNS3 format) -> EVE-NG icon (.png filename)
# EVE-NG only accepts .png filenames like "Firewall.png", NOT GNS3 paths like ":/symbols/firewall.svg"
ICON_MAP = {
    ":/symbols/firewall.svg":         "Firewall.png",
    ":/symbols/firewall2.svg":        "Firewall2.png",
    ":/symbols/Switch.png":           "Switch.png",
    ":/symbols/ethernet_switch.svg":  "Switch.png",
    ":/symbols/hub.svg":              "Switch.png",
    ":/symbols/Server.png":           "Server.png",
    ":/symbols/pc.svg":               "Desktop.png",
    ":/symbols/cloud.svg":            "Cloud.png",
    ":/symbols/router.svg":           "Router.png",
    ":/symbols/nat.svg":              "Cloud.png",
}

# Fallback icon by template key when YAML icon is unrecognized or missing
ICON_FALLBACK = {
    "nsfocusnf":       "Firewall.png",
    "huaweice6800":    "Switch.png",
    "linux":           "Desktop.png",
}

# Interface name mapping: template_key -> adapter -> iface_name
# EVE-NG uses real interface names, NOT eth0/0 format
# "linux" is dynamic: e{adapter}
IFACE_MAP = {
    "nsfocusnf": {
        0: "MEth0/0/0", 1: "Gi1/0", 2: "Gi2/0", 3: "Gi3/0", 4: "Gi4/0", 5: "Gi5/0",
    },
    "huaweice6800": {
        0: "MEth0/0/0", 1: "GE1/0/0", 2: "GE1/0/1", 3: "GE1/0/2",
    },
}


def get_iface(template_key, adapter):
    """Resolve real interface name for a given template and adapter."""
    if template_key == "linux":
        return f"e{adapter}"
    return IFACE_MAP.get(template_key, {}).get(adapter)


def parse_port(port_str):
    """Parse 'node_id:adapter/port' or 'node_id:adapter' -> (node_id, adapter, port)"""
    if ":" not in port_str:
        raise ValueError(f"Invalid port: {port_str}")
    node_id, rest = port_str.split(":", 1)
    if "/" in rest:
        adapter, port = rest.split("/", 1)
        return node_id, int(adapter), int(port)
    return node_id, int(rest), 0


def load_topology(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def count_adapter_usage(topo_nodes, topo_links):
    """Count required adapters per node by analyzing link usage."""
    usage = {}
    for link in topo_links:
        src, dst = link.get("src"), link.get("dst")
        if not src or not dst:
            continue
        for port_str in (src, dst):
            try:
                node_id, adapter, _ = parse_port(port_str)
                if node_id not in usage:
                    usage[node_id] = set()
                usage[node_id].add(adapter)
            except Exception:
                pass
    result = {}
    for node in topo_nodes:
        node_id = node["id"]
        adapters_used = usage.get(node_id, set())
        result[node_id] = max(adapters_used) + 1 if adapters_used else 1
    return result


def _get_client(host, port, username, password):
    """Connect and login to EVE-NG."""
    print(f"[INFO] Connecting to EVE-NG at {host}:{port}")
    client = EvengClient(host, protocol="http", port=port, disable_insecure_warnings=True)
    client.login(username=username, password=password)
    print(f"[OK] Logged in")
    return client


def _get_lab_node_id(client, lab_path, node_name):
    """Look up a node's EVE-NG ID by name. Returns (node_id, node_data) or (None, None)."""
    try:
        nodes_info = client.api.list_nodes(lab_path)
        nodes_data = nodes_info.get("data", nodes_info)
        if isinstance(nodes_data, dict):
            for nid, ndata in nodes_data.items():
                if ndata.get("name") == node_name:
                    return nid, ndata
    except Exception as e:
        print(f"[ERROR] Failed to list nodes: {e}")
    return None, None


def start_all(client, lab_path):
    """Start all nodes in the lab."""
    print(f"[INFO] Starting all nodes in {lab_path}...")
    try:
        client.api.start_all_nodes(lab_path)
        print("[OK] All nodes started")
    except Exception as e:
        print(f"[ERROR] Failed to start all nodes: {e}")
        sys.exit(1)


def stop_all(client, lab_path):
    """Stop all nodes in the lab."""
    print(f"[INFO] Stopping all nodes in {lab_path}...")
    try:
        client.api.stop_all_nodes(lab_path)
        print("[OK] All nodes stopped")
    except Exception as e:
        print(f"[ERROR] Failed to stop all nodes: {e}")
        sys.exit(1)


def start_node(client, lab_path, node_name):
    """Start a specific node by name."""
    node_id, ndata = _get_lab_node_id(client, lab_path, node_name)
    if not node_id:
        print(f"[ERROR] Node '{node_name}' not found in {lab_path}")
        sys.exit(1)
    status = ndata.get("status", -1)
    if status == 0:
        print(f"[INFO] Node '{node_name}' is already running")
        return
    print(f"[INFO] Starting node '{node_name}' (id={node_id})...")
    result = client.api.start_node(lab_path, node_id)
    code = result.get("code", 0)
    if code == 200:
        print(f"[OK] Node '{node_name}' started (console: {ndata.get('url', 'N/A')})")
    else:
        print(f"[WARN] Start node '{node_name}': {result}")


def stop_node(client, lab_path, node_name):
    """Stop a specific node by name."""
    node_id, ndata = _get_lab_node_id(client, lab_path, node_name)
    if not node_id:
        print(f"[ERROR] Node '{node_name}' not found in {lab_path}")
        sys.exit(1)
    status = ndata.get("status", -1)
    if status == 0:
        print(f"[INFO] Stopping node '{node_name}' (id={node_id})...")
        result = client.api.stop_node(lab_path, node_id)
        code = result.get("code", 0) if isinstance(result, dict) else 0
        if code == 200:
            print(f"[OK] Node '{node_name}' stopped")
        else:
            print(f"[WARN] Stop node '{node_name}': {result}")
    else:
        print(f"[INFO] Node '{node_name}' is already stopped")


def list_nodes(client, lab_path, topo_nodes=None):
    """List all nodes in the lab with console info."""
    print(f"\n[TELNET] Console addresses:")
    try:
        nodes_info = client.api.list_nodes(lab_path)
        nodes_data = nodes_info.get("data", nodes_info)
        if isinstance(nodes_data, dict) and nodes_data:
            names = list(nodes_data.values())
            max_len = max(len(nd.get("name", "?")) for nd in names) if names else 10
            for nid in sorted(nodes_data.keys(), key=lambda x: int(x) if x.isdigit() else x):
                ndata = nodes_data[nid]
                name = ndata.get("name", "?")
                url = ndata.get("url", "N/A")
                status = "running" if ndata.get("status") == 0 else "stopped"
                print(f"  {name:<{max_len}}  {url}  [{status}]")
    except Exception as e:
        print(f"[WARN] Could not retrieve node info: {e}")


def deploy(yaml_path, host, port=80, username="admin", password="eve",
           recreate=False, start_nodes=False):

    topo = load_topology(yaml_path)
    lab_name   = topo.get("name", "auto_lab")
    lab_desc   = topo.get("description", "")
    topo_nodes = topo.get("nodes", [])
    topo_links = topo.get("links", [])

    required_adapters = count_adapter_usage(topo_nodes, topo_links)

    print(f"[INFO] Connecting to EVE-NG at {host}:{port}")
    client = EvengClient(host, protocol="http", port=port, disable_insecure_warnings=True)
    client.login(username=username, password=password)
    print(f"[OK] Logged in")

    lab_path = f"/{lab_name}.unl"

    if recreate:
        try:
            client.api.delete_lab(lab_path)
            print(f"[INFO] Deleted existing lab: {lab_name}")
            time.sleep(1)
        except Exception as e:
            print(f"[WARN] Delete lab: {e}")

    try:
        client.api.create_lab(name=lab_name, path="/", author="auto", description=lab_desc)
        print(f"[OK] Created lab: {lab_name}")
    except Exception as e:
        if "already exists" in str(e) or "60016" in str(e):
            print(f"[INFO] Lab already exists, using it")
        else:
            print(f"[WARN] Create lab: {e}")

    yaml_id_to_name = {}
    name_to_template = {}

    print(f"[INFO] Creating {len(topo_nodes)} nodes...")
    for node in topo_nodes:
        yaml_id   = node["id"]
        name      = node["name"]
        node_type = node.get("node_type", "qemu")
        template  = node.get("template", "")
        image     = node.get("image")
        ram       = node.get("ram")
        cpu       = node.get("cpu")
        left      = node.get("left", 0)
        top       = node.get("top", 0)
        icon      = node.get("icon")
        eve_template = TEMPLATE_MAP.get(template, template)

        # Convert GNS3 icon path to EVE-NG .png filename
        if icon and icon in ICON_MAP:
            icon = ICON_MAP[icon]
        elif icon and icon.startswith(":/symbols/"):
            # Unknown GNS3 path — try to guess from filename
            guessed = icon.split("/")[-1].replace(".svg", ".png")
            icon = guessed if guessed in ICON_MAP.values() else None
        if not icon:
            icon = ICON_FALLBACK.get(eve_template, "Router.png")

        # Cloud/nat nodes are virtual networks - skip add_node
        if node_type == "nat":
            print(f"[SKIP] Cloud node '{name}' (virtual network, not a real node)")
            yaml_id_to_name[yaml_id] = name
            continue

        needed = required_adapters.get(yaml_id, 1)
        adapters = max(needed, node.get("adapters", 1) or 1, 1)

        try:
            client.api.add_node(
                path=lab_path,
                name=name,
                template=eve_template,
                node_type=node_type,
                top=int(top),
                left=int(left),
                console="telnet",
                ethernet=adapters,
                ram=ram,
                cpu=cpu,
                image=image,
                icon=icon,
            )
            print(f"[OK] Created node: {name} (template={eve_template}, adapters={adapters})")
            yaml_id_to_name[yaml_id] = name
            name_to_template[name] = eve_template
            time.sleep(0.4)
        except Exception as e:
            print(f"[SKIP] Node '{name}': {e}")

    # Pre-create cloud networks (nat nodes)
    cloud_networks = {}
    for link in topo_links:
        src, dst = link.get("src"), link.get("dst")
        if not src or not dst:
            continue
        src_id, _, _ = parse_port(src)
        dst_id, _, _ = parse_port(dst)
        for node_id in (src_id, dst_id):
            if node_id in cloud_networks:
                continue
            node_name = yaml_id_to_name.get(node_id, "")
            node_conf = next((n for n in topo_nodes if n["id"] == node_id), None)
            if node_conf and node_conf.get("node_type") == "nat":
                net_name = node_conf.get("name", f"net_{node_id}")
                net_type = node_conf.get("network_type", "pnet1")
                try:
                    r = client.api.add_lab_network(
                        lab_path,
                        network_type=net_type,
                        name=net_name,
                        visibility=1,
                        left=node_conf.get("left", 50),
                        top=node_conf.get("top", 50),
                    )
                    cloud_networks[node_id] = r.get("data", {}).get("id")
                    print(f"[OK] Created network '{net_name}' (type={net_type}) for cloud '{node_name}'")
                    time.sleep(0.3)
                except Exception as e:
                    print(f"[WARN] Create network for cloud '{node_name}': {e}")

    # Build interface cache: (node_name, adapter) -> iface_name
    node_iface_cache = {}
    for name, tmpl in name_to_template.items():
        node_iface_cache[(name,)] = tmpl  # store template per node

    def resolve_iface(node_yaml_id, port_str):
        _, adapter, _ = parse_port(port_str)
        node_name = yaml_id_to_name.get(node_yaml_id)
        if not node_name:
            return None
        tmpl = node_iface_cache.get((node_name,))
        if not tmpl:
            return None
        return get_iface(tmpl, adapter)

    # Create links
    print(f"[INFO] Creating {len(topo_links)} links...")
    links_ok = 0
    for link in topo_links:
        src = link.get("src")
        dst = link.get("dst")
        if not src or not dst:
            continue
        try:
            src_id, _, _ = parse_port(src)
            dst_id, _, _ = parse_port(dst)

            src_name = yaml_id_to_name.get(src_id)
            dst_name = yaml_id_to_name.get(dst_id)

            src_conf = next((n for n in topo_nodes if n["id"] == src_id), None)
            dst_conf = next((n for n in topo_nodes if n["id"] == dst_id), None)

            src_is_cloud = src_conf and src_conf.get("node_type") == "nat"
            dst_is_cloud = dst_conf and dst_conf.get("node_type") == "nat"

            if src_is_cloud:
                # cloud (src) -> node (dst): dst connects to cloud network
                dst_iface = resolve_iface(dst_id, dst)
                net_name  = src_conf.get("name")
                client.api.connect_node_to_cloud(
                    path=lab_path,
                    src=dst_name,
                    src_label=dst_iface,
                    dst=net_name,
                )
                print(f"[OK] Link: {dst_name}:{dst_iface} -> {net_name}")
                links_ok += 1

            elif dst_is_cloud:
                # node (src) -> cloud (dst): src connects to cloud network
                src_iface = resolve_iface(src_id, src)
                net_name  = dst_conf.get("name")
                client.api.connect_node_to_cloud(
                    path=lab_path,
                    src=src_name,
                    src_label=src_iface,
                    dst=net_name,
                )
                print(f"[OK] Link: {src_name}:{src_iface} -> {net_name}")
                links_ok += 1

            else:
                if not src_name or not dst_name:
                    print(f"[WARN] Skip link {src} <-> {dst}: unresolved node id")
                    continue

                src_iface = resolve_iface(src_id, src)
                dst_iface = resolve_iface(dst_id, dst)
                if not src_iface or not dst_iface:
                    print(f"[WARN] Skip link {src} <-> {dst}: could not resolve interface")
                    continue

                client.api.connect_node_to_node(
                    path=lab_path,
                    src=src_name,
                    src_label=src_iface,
                    dst=dst_name,
                    dst_label=dst_iface,
                )
                print(f"[OK] Link: {src_name}:{src_iface} <-> {dst_name}:{dst_iface}")
                links_ok += 1

            time.sleep(0.4)
        except Exception as e:
            print(f"[SKIP] Link {src} <-> {dst}: {e}")

    if start_nodes:
        print("[INFO] Starting all nodes...")
        client.api.start_all_nodes(lab_path)

    print(f"\n[SUCCESS] '{lab_name}' deployed!")
    print(f"  Nodes : {len(name_to_template)}/{len(topo_nodes)}")
    print(f"  Links : {links_ok}/{len(topo_links)}")
    print(f"  URL   : http://{host}/lab/{lab_name}.unl")

    # Print telnet console info for all nodes
    try:
        nodes_info = client.api.list_nodes(lab_path)
        nodes_data = nodes_info.get("data", nodes_info)
        if isinstance(nodes_data, dict) and nodes_data:
            print(f"\n[TELNET] Console addresses (for downstream skill consumption):")
            max_len = max(len(ndata.get("name", "?")) for ndata in nodes_data.values())
            # Output in YAML node order for consistency
            yaml_node_order = {n["name"]: n for n in topo_nodes if n.get("node_type") != "nat"}
            for node_conf in topo_nodes:
                name = node_conf["name"]
                if node_conf.get("node_type") == "nat":
                    continue
                # Find matching node in EVE-NG response
                for nid, ndata in nodes_data.items():
                    if ndata.get("name") == name:
                        url = ndata.get("url", "N/A")
                        template = node_conf.get("template", "?")
                        print(f"  {name:<{max_len}}  {url}  template={TEMPLATE_MAP.get(template, template)}")
                        break
    except Exception as e:
        print(f"[WARN] Could not retrieve console info: {e}")


if __name__ == "__main__":
    # Backward compat: no subcommand → default to "deploy"
    if len(sys.argv) >= 2 and sys.argv[1] in ("deploy", "start", "stop", "list"):
        subcmd = sys.argv.pop(1)
    else:
        subcmd = "deploy"

    parser = argparse.ArgumentParser(description="EVE-NG topology manager")

    if subcmd == "deploy":
        parser.add_argument("yaml", help="Topology YAML file")
        parser.add_argument("--host", default="localhost", help="EVE-NG host/IP")
        parser.add_argument("--port", type=int, default=80, help="API port (default 80)")
        parser.add_argument("--user", default="admin", help="Username")
        parser.add_argument("--password", default="eve", help="Password")
        parser.add_argument("--recreate", action="store_true", help="Delete and recreate lab")
        parser.add_argument("--start", action="store_true", help="Start nodes after deploy")
        args = parser.parse_args()
        deploy(
            yaml_path=args.yaml,
            host=args.host,
            port=args.port,
            username=args.user,
            password=args.password,
            recreate=args.recreate,
            start_nodes=args.start,
        )
    else:
        parser.add_argument("yaml", help="Topology YAML file")
        parser.add_argument("--host", default="localhost", help="EVE-NG host/IP")
        parser.add_argument("--port", type=int, default=80, help="API port (default 80)")
        parser.add_argument("--user", default="admin", help="Username")
        parser.add_argument("--password", default="eve", help="Password")
        parser.add_argument("--lab", default=None, help="Lab name (overrides YAML name)")
        parser.add_argument("--node", default=None, help="Node name (omit for all nodes)")
        args = parser.parse_args()

        topo = load_topology(args.yaml)
        lab_name = args.lab or topo.get("name", "auto_lab")
        lab_path = f"/{lab_name}.unl"
        client = _get_client(args.host, args.port, args.user, args.password)

        if subcmd == "start":
            if args.node:
                start_node(client, lab_path, args.node)
            else:
                start_all(client, lab_path)
        elif subcmd == "stop":
            if args.node:
                stop_node(client, lab_path, args.node)
            else:
                stop_all(client, lab_path)
        elif subcmd == "list":
            list_nodes(client, lab_path, topo.get("nodes"))
