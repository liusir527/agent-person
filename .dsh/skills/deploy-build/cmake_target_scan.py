#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cmake_target_scan.py - 改动影响产物扫描工具 (ninja 生成器)

在编译机上执行，从 build.ninja 建立「源文件 → 编译目标 → 链接产物(.so/.a)」
映射，找出受改动文件影响的所有 lib/plugin 产物，供 deploy_build.py 精确同步到设备。

为什么解析 build.ninja 而不是 CMakeCache.txt:
  nsbuild 实际用 ninja 生成器构建 (build.ninja + rules.ninja)，
  CMakeCache.txt 不包含目标描述，CMakeFiles/<target>.dir/build.make|link.txt
  在 ninja 下也不生成。ninja 的 build 语句天然表达了
  "输出 ← 输入(源文件/对象文件)" 的关系。

用法:
  python3 cmake_target_scan.py \\
    --build-dir /path/to/build-root/build-x86_64/vpp \\
    --install-dir /path/to/nf/.nsbuild/install/edisk \\
    --changed-files src/plugins/npp_debug/npp_debug.c include/...

说明:
  --build-dir 是 nsbuild 的真实 CMake 构建目录（含 build.ninja/CMakeCache.txt），
    即 ${remote_npp_dir}/build-root/build-<arch>/vpp。
  --install-dir 是 nsbuild-git -di 生成的打包产物目录（nf/.nsbuild/install/edisk）。

输出: JSON 格式 (stdout)，供 deploy_build.py 消费
  核心字段:
    artifacts: [{ rel: "<edisk相对路径>", target: "<目标名>", type: "SHARED_LIBRARY|..." }]
    affected_targets: [目标名, ...]

依赖: 仅 Python 标准库
"""

import argparse
import json
import os
import re
import sys

# 远端环境可能为 ascii locale / python 3.6（无 sys.stdout.reconfigure），
# 显式用 utf-8 输出避免 print 中文 JSON 崩溃（依赖 PYTHONIOENCODING=utf-8 双保险）。
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


# === build.ninja 解析 ===

# 目标名从 rule 提取: C_COMPILER__<target> / CXX_COMPILER__<target> / C_SHARED_LIBRARY_LINKER__<target> ...
_RULE_TARGET_RE = re.compile(r"(?:^| )(\w+)__(.+?)(?: |$)")
# 相对路径段(如 src/plugins/npp_debug/npp_debug.c) 匹配改动文件
# ninja build 行的绝对/相对源路径
_BUILD_LINE_RE = re.compile(r"^build\s+([^:]+):\s*([^\s]+)\s+(.+)$")


def parse_build_ninja(build_dir):
    """解析 build.ninja，建立源文件→目标 与 目标→产物 映射。

    返回:
        {
            "src_to_targets": { "<源文件相对/绝对路径>": {target: True} },
            "target_to_artifact": { "<target>": "<产物相对路径如 lib/vpp_plugins/x.so>" },
            "all_targets": [<target>, ...],
        }
    """
    ninja_file = os.path.join(build_dir, "build.ninja")
    src_to_targets = {}
    target_to_artifact = {}
    all_targets = set()

    if not os.path.isfile(ninja_file):
        print(f"[SCAN-WARN] build.ninja 不存在: {ninja_file}", file=sys.stderr)
        return {"src_to_targets": {}, "target_to_artifact": {}, "all_targets": []}

    try:
        with open(ninja_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except IOError as e:
        print(f"[SCAN-WARN] 读取 build.ninja 失败: {e}", file=sys.stderr)
        return {"src_to_targets": {}, "target_to_artifact": {}, "all_targets": []}

    # 当前 build 行的 pending 变量(TARGET_FILE 等)
    for line in lines:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        # 变量行 (缩进 + KEY = VALUE)
        m_var = re.match(r"^\s+(\w+)\s*=\s*(.*)$", line)
        if m_var:
            k, v = m_var.group(1), m_var.group(2)
            if k == "TARGET_FILE" and cur_artifact:
                # TARGET_FILE = lib/vpp_plugins/npp_debug_plugin.so
                target_to_artifact[cur_target] = v.strip()
            continue

        m = _BUILD_LINE_RE.match(line)
        if not m:
            continue
        outputs_raw, rule, inputs_raw = m.group(1), m.group(2), m.group(3)
        outputs = [o.strip() for o in outputs_raw.split() if o.strip()]
        inputs = [i.strip() for i in inputs_raw.split() if i.strip()]
        cur_output = outputs[0] if outputs else ""
        cur_artifact = cur_output if cur_output.endswith((".so", ".a", ".so.")) else None

        # 从 rule 提取目标名
        rm = _RULE_TARGET_RE.search(rule)
        cur_target = None
        if rm:
            cur_target = rm.group(2).strip()
            all_targets.add(cur_target)
            # 链接边: 产物直接关联目标 (C_SHARED_LIBRARY_LINKER__<target>)
            if cur_artifact and cur_target:
                target_to_artifact[cur_target] = cur_artifact

        # 编译边: build <x>.o: C_COMPILER__<target> /abs/src/foo.c ...
        if cur_target and cur_output.endswith(".o"):
            for src in inputs:
                # 只保留 .c/.cc/.cpp/.S 源文件(跳过头文件/生成文件/|| 依赖)
                if src.endswith((".c", ".cc", ".cpp", ".cxx", ".S", ".s")):
                    # 记录原始路径 + basename + 相对段, 提高匹配命中率
                    src_to_targets.setdefault(src, {})[cur_target] = True
                    base = os.path.basename(src)
                    src_to_targets.setdefault(base, {})[cur_target] = True
                    # 相对仓库根的路径段(去掉绝对前缀)
                    m_rel = re.search(r"/(?:src|include)/.*", src)
                    if m_rel:
                        src_to_targets.setdefault(m_rel.group(0).lstrip("/"), {})[cur_target] = True

    return {
        "src_to_targets": src_to_targets,
        "target_to_artifact": target_to_artifact,
        "all_targets": sorted(all_targets),
    }


# === 改动文件匹配 ===


def _clean_surrogates(s):
    """清洗 surrogateescape 污染的字符串。

    远端 ascii locale 下 argv 中文字符会被 surrogateescape 破坏(如 \udce9...)，
    导致 json.dumps 时 'surrogates not allowed' 崩溃。将这些低代理序列按
    UTF-8 字节重新解码还原。
    """
    if not any(0xDC80 <= ord(c) <= 0xDCFF for c in s):
        return s
    try:
        return s.encode("utf-8", errors="surrogateescape").decode("utf-8", errors="ignore")
    except Exception:
        return s


def find_affected_targets(changed_files, src_to_targets, target_to_artifact):
    """根据改动文件找出受影响目标。

    匹配策略:
      1. 精确匹配源文件路径(相对/绝对)
      2. basename 匹配(同名不同目录, 保守命中)
      3. 头文件: 若改动文件是 .h, 用"目录前缀"匹配——源文件路径包含该头文件所在目录段
         (如 src/plugins/npp_debug/npp_debug.h → 命中 src/plugins/npp_debug/ 下所有源)
    """
    affected = set()
    changed_set = [os.path.normpath(f) for f in changed_files]
    headers = [f for f in changed_files if f.endswith((".h", ".hpp"))]
    src_changes = [f for f in changed_files if f.endswith((".c", ".cc", ".cpp", ".cxx", ".S", ".s"))]

    # 1) 源文件精确/basename 匹配
    for src in src_changes:
        base = os.path.basename(src)
        for key in (src, base, src.lstrip("/")):
            for tgt in src_to_targets.get(key, {}):
                affected.add(tgt)

    # 2) 头文件目录前缀匹配: 命中同目录/子目录的源文件
    for h in headers:
        h_dir = os.path.dirname(h)  # 如 src/plugins/npp_debug
        h_dir_norm = os.path.normpath(h_dir).replace("\\", "/")
        for src, tgts in src_to_targets.items():
            # 源路径含头文件所在目录(相对段) 则命中
            if "/" + h_dir_norm + "/" in src or src.startswith(h_dir_norm + "/"):
                for tgt in tgts:
                    affected.add(tgt)

    # 3) CMakeLists 改动: 保守处理——命中同目录下的所有目标
    for cf in changed_files:
        if os.path.basename(cf) == "CMakeLists.txt":
            cf_dir = os.path.dirname(cf).replace("\\", "/")
            for src, tgts in src_to_targets.items():
                if cf_dir and (("/" + cf_dir + "/") in src or src.startswith(cf_dir + "/")):
                    for tgt in tgts:
                        affected.add(tgt)

    return affected


# === 产物定位 ===


def find_artifacts(affected_targets, install_dir, target_to_artifact):
    """受影响的产物 → edisk 相对路径。

    优先用 ninja 的 TARGET_FILE 定位(build 树相对路径, 如 lib/vpp_plugins/x.so)；
    再在 install_dir(edisk) 里按产物名递归找同名文件。
    返回 [{rel, target, type}], rel 为 edisk 相对路径(如 nsfocus/product/lib/vpp_plugins/x.so)。
    """
    artifacts = []
    seen = set()
    for tgt in sorted(affected_targets):
        artifact_rel = target_to_artifact.get(tgt)
        fname = os.path.basename(artifact_rel) if artifact_rel else (tgt + ".so")

        # 在 edisk 里定位同名文件
        rel_path = None
        if install_dir and os.path.isdir(install_dir):
            for root, dirs, files in os.walk(install_dir):
                for fn in files:
                    if fn == fname:
                        full = os.path.join(root, fn)
                        rel_path = os.path.relpath(full, install_dir).replace("\\", "/")
                        break
                if rel_path:
                    break
        if not rel_path and artifact_rel:
            # 退路: 用 TARGET_FILE 相对路径猜 edisk 位置
            guess = os.path.join("nsfocus", "product", artifact_rel)
            if os.path.isfile(os.path.join(install_dir, guess)):
                rel_path = guess.replace("\\", "/")

        if rel_path and rel_path not in seen:
            seen.add(rel_path)
            artifacts.append({
                "rel": rel_path,
                "target": tgt,
                "type": "SHARED_LIBRARY" if fname.endswith(".so") else "LIBRARY",
            })
        elif not rel_path:
            print(f"[SCAN-WARN] 受影响目标 {tgt} 产物未在 edisk 定位到: {fname}", file=sys.stderr)
    return artifacts


# === 主流程 ===


def main():
    parser = argparse.ArgumentParser(
        description="改动影响产物扫描(ninja): 找受改动文件影响的 lib/plugin 产物"
    )
    parser.add_argument("--build-dir", required=True, help="CMake 构建目录(含 build.ninja)")
    parser.add_argument("--install-dir", required=True, help="安装产物目录(.nsbuild/install/edisk)")
    parser.add_argument("--changed-files", nargs="+", required=True, help="改动文件列表(相对路径)")
    args = parser.parse_args()

    build_dir = os.path.abspath(args.build_dir)
    install_dir = os.path.abspath(args.install_dir)
    # 清洗 argv 中可能被 surrogateescape 污染的中文文件名，避免 json.dumps 崩溃
    args.changed_files = [_clean_surrogates(f) for f in args.changed_files]

    if not os.path.isdir(build_dir):
        print(json.dumps({"error": f"构建目录不存在: {build_dir}"}, ensure_ascii=False))
        sys.exit(1)
    if not os.path.isdir(install_dir):
        print(json.dumps({"error": f"安装目录不存在: {install_dir}"}, ensure_ascii=False))
        sys.exit(1)

    # 1. 解析 build.ninja
    graph = parse_build_ninja(build_dir)
    src_to_targets = graph["src_to_targets"]
    target_to_artifact = graph["target_to_artifact"]
    all_targets = graph["all_targets"]
    print(f"[SCAN] ninja 目标数: {len(all_targets)}, 产物映射数: {len(target_to_artifact)}", file=sys.stderr)

    if not all_targets:
        print(json.dumps({
            "error": "未解析到任何目标，请确认 --build-dir 下存在有效的 build.ninja",
            "build_dir": build_dir,
        }, ensure_ascii=False))
        sys.exit(1)

    # 2. 找出受影响的编译目标
    affected = find_affected_targets(args.changed_files, src_to_targets, target_to_artifact)
    if not affected:
        print("[SCAN] 未找到受影响的目标", file=sys.stderr)

    # 3. 定位 edisk 产物
    artifacts = find_artifacts(affected, install_dir, target_to_artifact)

    # 4. 输出 JSON
    result = {
        "affected_targets": sorted(affected),
        "artifacts": artifacts,
        "changed_files": args.changed_files,
        "summary": {
            "total_targets": len(all_targets),
            "affected_count": len(affected),
            "artifact_count": len(artifacts),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
