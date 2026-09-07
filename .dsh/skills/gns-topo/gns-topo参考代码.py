#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GNS3 Topology Automation Script
Read topology from YAML and auto-deploy to GNS3 server
"""

import yaml
import requests
import sys
import time

SIMPLE_NODE_TYPES = {
    "cloud", "nat", "ethernet_switch", "ethernet_hub",
    "vpcs", "frame_relay_switch", "atm_switch",
}

_DEFAULT_SYMBOLS = {
    "ethernet_switch": ":/symbols/ethernet_switch.svg",
    "ethernet_hub":    ":/symbols/hub.svg",
    "cloud":           ":/symbols/cloud.svg",
    "nat":             ":/symbols/cloud.svg",
}


def _normalize_name(value):
    if value is None:
        return ""
    return str(value).strip().lower()


class GNS3Client:
    def __init__(self, host="localhost", port=3080, username=None, password=None):
        self.base_url = f"http://{host}:{port}/v2"
        self.session = requests.Session()
        if username and password:
            self.session.auth = (username, password)

    def get_projects(self):
        resp = self.session.get(f"{self.base_url}/projects")
        resp.raise_for_status()
        return resp.json()

    def get_project_by_name(self, name):
        for proj in self.get_projects():
            if proj.get("name") == name:
                return proj
        return None

    def create_project(self, name, **kwargs):
        existing = self.get_project_by_name(name)
        if existing:
            print(f"[INFO] Project '{name}' already exists, reusing it.")
            return existing
        payload = {"name": name}
        # GNS3 2.2.x does not accept 'description' in POST /projects
        payload.update({k: v for k, v in kwargs.items() if k != "description"})
        resp = self.session.post(f"{self.base_url}/projects", json=payload)
        if resp.status_code >= 400:
            print(f"[ERROR] Create project failed: {resp.status_code} {resp.text}")
        resp.raise_for_status()
        print(f"[OK] Created project: {name}")
        return resp.json()

    def delete_project(self, project_id):
        resp = self.session.delete(f"{self.base_url}/projects/{project_id}")
        resp.raise_for_status()
        print(f"[OK] Deleted project: {project_id}")

    def get_project_nodes(self, project_id):
        resp = self.session.get(f"{self.base_url}/projects/{project_id}/nodes")
        resp.raise_for_status()
        return resp.json()

    def get_templates(self):
        resp = self.session.get(f"{self.base_url}/templates")
        resp.raise_for_status()
        return resp.json()

    def get_template_by_name(self, name):
        wanted = _normalize_name(name)
        for t in self.get_templates():
            if (
                _normalize_name(t.get("name")) == wanted
                or _normalize_name(t.get("template_id")) == wanted
            ):
                return t
        return None

    def get_template(self, template_id):
        resp = self.session.get(f"{self.base_url}/templates/{template_id}")
        if resp.status_code == 200:
            return resp.json()
        return None

    def get_computes(self):
        resp = self.session.get(f"{self.base_url}/computes")
        resp.raise_for_status()
        return resp.json()

    def create_node(self, project_id, name, node_type="qemu", template_id=None,
                    compute_id="local", properties=None, x=0, y=0, symbol=None):
        payload = {
            "name": name,
            "node_type": node_type,
            "compute_id": compute_id,
            "x": int(x),
            "y": int(y),
        }
        if symbol:
            payload["symbol"] = symbol
        if template_id:
            payload["template_id"] = template_id
        if properties:
            payload.setdefault("properties", {})
            payload["properties"].update(properties)

        resp = self.session.post(
            f"{self.base_url}/projects/{project_id}/nodes",
            json=payload
        )
        if resp.status_code != 201:
            print(f"[ERROR] Failed to create node '{name}': {resp.text}")
            raise RuntimeError(f"Create node failed: {resp.text}")
        print(f"[OK] Created node: {name} (type={node_type})")
        return resp.json()

    def create_link(self, project_id, node_a, adapter_a, port_a,
                    node_b, adapter_b, port_b):
        payload = {
            "nodes": [
                {
                    "node_id": node_a,
                    "adapter_number": int(adapter_a),
                    "port_number": int(port_a),
                },
                {
                    "node_id": node_b,
                    "adapter_number": int(adapter_b),
                    "port_number": int(port_b),
                },
            ]
        }
        resp = self.session.post(
            f"{self.base_url}/projects/{project_id}/links",
            json=payload
        )
        if resp.status_code != 201:
            print(f"[ERROR] Failed to create link: {resp.text}")
            raise RuntimeError(f"Create link failed: {resp.text}")
        print(f"[OK] Created link: {node_a}:{adapter_a}/{port_a} <-> {node_b}:{adapter_b}/{port_b}")
        return resp.json()

    def start_node(self, project_id, node_id):
        resp = self.session.post(
            f"{self.base_url}/projects/{project_id}/nodes/{node_id}/start"
        )
        if resp.status_code == 200 or resp.status_code == 204:
            print(f"[OK] Started node: {node_id}")
        else:
            print(f"[WARN] Could not start node {node_id}: {resp.status_code}")

    def start_all_nodes(self, project_id):
        resp = self.session.post(
            f"{self.base_url}/projects/{project_id}/nodes/start"
        )
        if resp.status_code == 200 or resp.status_code == 204:
            print("[OK] Started all nodes")
        else:
            print(f"[WARN] Could not start all nodes: {resp.status_code}")


def parse_port(port_str: str):
    """Parse 'R1:0/0' or 'R1:0' into (node_name, adapter, port)."""
    if ":" not in port_str:
        raise ValueError(f"Invalid port string: {port_str}, expected format 'NodeName:adapter/port' or 'NodeName:adapter'")
    node_name, rest = port_str.split(":", 1)
    if "/" in rest:
        adapter, port = rest.split("/", 1)
        return node_name, int(adapter), int(port)
    else:
        # default port 0 if not specified
        return node_name, int(rest), 0


def _make_switch_ports(num_ports: int) -> list:
    """Generate a default ports_mapping for an ethernet_switch with access ports on VLAN 1."""
    return [
        {"name": f"Ethernet{i}", "port_number": i, "type": "access", "vlan": 1}
        for i in range(num_ports)
    ]


def load_topology(yaml_path: str):
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


def resolve_template(client: GNS3Client, node_conf: dict):
    """
    Try to find the best matching template for a node configuration.
    Returns (template_id, node_type, properties) or (None, node_type, properties).
    
    Key fix: For templates like linux-ubuntu22.04 that have pre-configured images,
    do NOT override hda_disk_image - let the server template handle it.
    """
    node_type = node_conf.get("node_type", "qemu")

    # Simple node types (cloud, nat, etc.) need no template lookup
    if node_type in SIMPLE_NODE_TYPES:
        return None, node_type, {}

    template_name = node_conf.get("template")
    image = node_conf.get("image")

    properties = {}
    
    # CRITICAL FIX: Only set image explicitly when NO template is used
    # If template exists with its own image config, don't override it
    # This prevents "The image xxx is missing" errors for template-based nodes
    if image and not template_name:
        properties["hda_disk_image"] = image

    # Allow raw qemu creation when a server-side template is unavailable.
    for yaml_key, prop_key in {
        "ram": "ram",
        "adapters": "adapters",
        "adapter_type": "adapter_type",
        "console_type": "console_type",
        "qemu_path": "qemu_path",
        "options": "options",
    }.items():
        if node_conf.get(yaml_key) is not None:
            properties[prop_key] = node_conf[yaml_key]

    platform = node_conf.get("platform") or node_conf.get("cpu_type")
    if platform:
        properties.setdefault("platform", platform)

    if template_name:
        tmpl = client.get_template_by_name(template_name)
        if tmpl:
            tmpl_id = tmpl.get("template_id")
            print(f"[INFO] Found template '{template_name}' -> {tmpl_id}")

            # Fetch full template details to merge missing properties
            full_tmpl = client.get_template(tmpl_id)
            if full_tmpl:
                # Merge critical template properties that GNS3 needs
                for key in ["platform", "arch", "ram", "adapters", "adapter_type",
                            "console_type", "boot_priority", "cpu_throttling",
                            "process_priority", "options", "kernel_image",
                            "kernel_command_line", "initrd", "bios_image",
                            "cdrom_image", "hda_disk_image", "hdb_disk_image",
                            "hdc_disk_image", "hdd_disk_image", "qemu_path"]:
                    if key in full_tmpl and full_tmpl[key] is not None:
                        properties.setdefault(key, full_tmpl[key])

                # Fix common issue: platform is None/empty causing qemu-system-None error
                if properties.get("platform") in (None, "", "None"):
                    properties["platform"] = "x86_64"
                    print(f"[WARN] Template '{template_name}' has no platform, defaulting to x86_64")

                node_type = full_tmpl.get("template_type", node_type)
            return tmpl_id, node_type, properties
        else:
            print(f"[WARN] Template '{template_name}' not found on GNS3 server")
            # For Ubuntu nodes, template is REQUIRED since they don't have standalone images
            if "ubuntu" in template_name.lower() or "linux" in template_name.lower():
                print(f"[ERROR] Ubuntu/Linux nodes require a valid template - cannot create without one")
                return None, "unavailable", {"error": f"Template '{template_name}' not found"}
            print(f"[WARN] Falling back to node_type='{node_type}'")

    if node_type == "qemu" and properties.get("platform") in (None, "", "None"):
        properties["platform"] = "x86_64"
        print("[WARN] QEMU node has no platform, defaulting to x86_64")

    return None, node_type, properties


def _record_console(console_map: dict, name: str, node: dict, server_host: str = ""):
    console_type = node.get("console_type", "")
    console_port = node.get("console")
    console_host = node.get("console_host", "") or ""
    if console_host in ("0.0.0.0", "::") and server_host:
        console_host = server_host
    if console_type and console_type != "none" and console_port:
        console_map[name] = {"host": console_host, "port": console_port, "type": console_type}


def _register_node_aliases(node_map: dict, node_id: str, node_conf: dict):
    yaml_id = node_conf.get("id")
    yaml_name = node_conf.get("name")
    if yaml_id:
        node_map[yaml_id] = node_id
    if yaml_name:
        node_map[yaml_name] = node_id


def _register_alias_value(alias_map: dict, value: str, payload: str):
    if value:
        alias_map[value] = payload


def _register_link_mode(link_mode_map: dict, node_conf: dict, mode: str):
    _register_alias_value(link_mode_map, node_conf.get("id"), mode)
    _register_alias_value(link_mode_map, node_conf.get("name"), mode)


def _normalize_link_endpoint(node_name: str, adapter: int, port: int, link_mode_map: dict):
    mode = link_mode_map.get(node_name)
    if mode == "qemu_switch" and adapter == 0 and port > 0:
        return adapter + port, 0
    return adapter, port


def deploy_topology(yaml_path: str, host="localhost", port=3080, start_nodes=False,
                     username=None, password=None, recreate=False):
    topo = load_topology(yaml_path)
    project_name = topo.get("name", "auto_lab")
    project_desc = topo.get("description", "")
    topo_nodes = topo.get("nodes", [])

    client = GNS3Client(host=host, port=port, username=username, password=password)

    # Verify server reachable
    try:
        client.get_projects()
    except requests.exceptions.ConnectionError as e:
        print(f"[FATAL] Cannot connect to GNS3 server at {host}:{port}: {e}")
        sys.exit(1)

    # Create (or reuse/recreate) project
    if recreate:
        existing = client.get_project_by_name(project_name)
        if existing:
            client.delete_project(existing["project_id"])
            print(f"[INFO] Recreating project '{project_name}'")
    project = client.create_project(project_name, description=project_desc)
    project_id = project["project_id"]

    prepared_nodes = []
    link_mode_map = {}
    for n in topo_nodes:
        tmpl_id, resolved_node_type, resolved_props = resolve_template(client, n)
        prepared_nodes.append({
            "conf": n,
            "template_id": tmpl_id,
            "resolved_node_type": resolved_node_type,
            "resolved_props": resolved_props,
        })
        if n.get("node_type") == "qos_sw" and resolved_node_type == "qemu":
            _register_link_mode(link_mode_map, n, "qemu_switch")

    # Pre-populate node_map with nodes that already exist in the project
    node_map = {}
    console_map = {}
    existing_nodes_by_name = {}
    for existing_node in client.get_project_nodes(project_id):
        existing_nodes_by_name[existing_node["name"]] = existing_node
        node_map[existing_node["name"]] = existing_node["node_id"]
        _record_console(console_map, existing_node["name"], existing_node, host)
    for n in topo_nodes:
        existing_node = existing_nodes_by_name.get(n.get("name"))
        if existing_node:
            _register_node_aliases(node_map, existing_node["node_id"], n)
    if existing_nodes_by_name:
        print(f"[INFO] Found {len(existing_nodes_by_name)} existing node(s) in project, skipping re-creation.")

    # Create nodes
    for prepared in prepared_nodes:
        n = prepared["conf"]
        name = n["name"]
        x = n.get("left", n.get("x", 0))
        y = n.get("top", n.get("y", 0))

        if name in existing_nodes_by_name:
            print(f"[SKIP] Node '{name}' already exists, skipping.")
            continue

        tmpl_id = prepared["template_id"]
        node_type = prepared["resolved_node_type"]
        
        # Skip nodes that couldn't be resolved (e.g., Ubuntu without template)
        if node_type == "unavailable":
            print(f"[SKIP] Skipping {name} - cannot create without valid template")
            continue
            
        props = dict(prepared["resolved_props"])
        # Merge user-supplied properties from YAML (overrides template defaults)
        props.update(n.get("properties", {}))
        # Convenience: auto-generate ports_mapping for ethernet_switch via num_ports
        if node_type in ("ethernet_switch", "ethernet_hub"):
            props.setdefault("console_type", "none")
            if "num_ports" in n and "ports_mapping" not in props:
                props["ports_mapping"] = _make_switch_ports(n["num_ports"])

        symbol = n.get("symbol", _DEFAULT_SYMBOLS.get(node_type))

        # Cloud/NAT nodes must run on the local compute
        compute_id = n.get("compute_id", "local")
        if node_type in SIMPLE_NODE_TYPES and compute_id != "local":
            print(f"[WARN] Node '{name}' is type '{node_type}' — forcing compute_id=local")
            compute_id = "local"

        try:
            node = client.create_node(
                project_id=project_id,
                name=name,
                node_type=node_type,
                template_id=tmpl_id,
                compute_id=compute_id,
                x=x,
                y=y,
                symbol=symbol,
                properties=props,
            )
            _register_node_aliases(node_map, node["node_id"], n)
            existing_nodes_by_name[name] = node
            _record_console(console_map, name, node, host)
        except Exception as e:
            print(f"[SKIP] Failed to create {name}: {e}")
        # Small delay to avoid flooding the server
        time.sleep(0.2)

    # Create links
    links_created = 0
    for lnk in topo.get("links", []):
        src = lnk.get("src")
        dst = lnk.get("dst")
        if not src or not dst:
            print(f"[WARN] Skipping invalid link (missing src/dst): {lnk}")
            continue

        src_node, src_adapter, src_port = parse_port(src)
        dst_node, dst_adapter, dst_port = parse_port(dst)
        src_adapter, src_port = _normalize_link_endpoint(src_node, src_adapter, src_port, link_mode_map)
        dst_adapter, dst_port = _normalize_link_endpoint(dst_node, dst_adapter, dst_port, link_mode_map)

        if src_node not in node_map or dst_node not in node_map:
            print(f"[WARN] Skipping link because node not found: {src_node} <-> {dst_node}")
            continue

        client.create_link(
            project_id=project_id,
            node_a=node_map[src_node],
            adapter_a=src_adapter,
            port_a=src_port,
            node_b=node_map[dst_node],
            adapter_b=dst_adapter,
            port_b=dst_port,
        )
        links_created += 1
        time.sleep(0.2)

    if start_nodes:
        client.start_all_nodes(project_id)

    print(f"\n[SUCCESS] Topology '{project_name}' deployed to GNS3!")
    print(f"          Project ID: {project_id}")
    print(f"          Nodes: {len(existing_nodes_by_name)}")
    print(f"          Links: {links_created}/{len(topo.get('links', []))}")

    if console_map:
        print("\n[TELNET] Console addresses:")
        ordered_names = [n["name"] for n in topo_nodes if n.get("name") in existing_nodes_by_name]
        max_len = max(len(n) for n in ordered_names)
        for node_name in ordered_names:
            info = console_map.get(node_name)
            if info:
                print(f"  {node_name:<{max_len}}  telnet {info['host']} {info['port']}")
            else:
                print(f"  {node_name:<{max_len}}  (no console)")

    return {"project_id": project_id, "node_map": node_map, "console_map": console_map}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Deploy YAML topology to GNS3")
    parser.add_argument("yaml", nargs="?", default="my_topology.yaml", help="Path to topology YAML file")
    parser.add_argument("--host", default="localhost", help="GNS3 server host")
    parser.add_argument("--port", type=int, default=3080, help="GNS3 server port")
    parser.add_argument("--user", default=None, help="GNS3 username (HTTP Basic Auth)")
    parser.add_argument("--password", default=None, help="GNS3 password (HTTP Basic Auth)")
    parser.add_argument("--start", action="store_true", help="Auto-start all nodes after deployment")
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate the project if it already exists")
    args = parser.parse_args()

    deploy_topology(args.yaml, host=args.host, port=args.port, start_nodes=args.start,
                    username=args.user, password=args.password, recreate=args.recreate)