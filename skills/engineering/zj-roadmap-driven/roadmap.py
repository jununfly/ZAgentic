"""
zj-roadmap-driven — 路线图核心数据模型

确定性操作：所有方法都是纯函数，输入确定则输出确定。
JSON 是唯一真相源，Markdown 只是渲染视图。
"""

import json
import os
from datetime import datetime
from typing import Optional, Any

# ── 状态常量 ──────────────────────────────────────────────
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_BLOCKED = "blocked"

STATUS_ICONS = {
    STATUS_PENDING: "[ ]",
    STATUS_IN_PROGRESS: "[~]",
    STATUS_COMPLETED: "[x]",
    STATUS_BLOCKED: "[!]",
}

MODE_EXPLORE = "explore"
MODE_EXPLOIT = "exploit"

MODE_TAG = {
    MODE_EXPLORE: "[X+]",
    MODE_EXPLOIT: "[Y+]",
}

# ── 节点 ID 生成 ──────────────────────────────────────────

def gen_child_id(parent_id: str, index: int) -> str:
    """从父节点 id 生成子节点 id。
    "1" + 1 → "1-1", "1-1" + 2 → "1-1-2"
    """
    if parent_id == "":
        return str(index)
    return f"{parent_id}-{index}"


def next_child_index(roadmap: dict, parent_id: str) -> int:
    """计算父节点下下一个子节点的序号。"""
    parent = roadmap["nodes"].get(parent_id)
    if not parent or not parent["children"]:
        return 1
    # 从最后一个 child id 提取序号
    last = parent["children"][-1]
    parts = last.split("-")
    return int(parts[-1]) + 1


def node_depth(node_id: str) -> int:
    """节点深度。1 → 1, 1-1 → 2, 1-1-1 → 3"""
    return node_id.count("-") + 1


def parent_id_of(node_id: str) -> Optional[str]:
    """获取父节点 id。1-1 → 1, 1 → None"""
    parts = node_id.rsplit("-", 1)
    if len(parts) == 1:
        return None
    return parts[0]


# ── Roadmap 类 ────────────────────────────────────────────

class Roadmap:
    """路线图核心类。"""

    def __init__(self, json_path: str):
        self.json_path = os.path.abspath(json_path)
        self.data: dict = {}

    # ── 文件 I/O ───────────────────────────────────────

    def load(self) -> dict:
        """从 JSON 文件加载路线图数据。"""
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"路线图文件不存在: {self.json_path}")
        with open(self.json_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        return self.data

    def save(self) -> str:
        """保存路线图数据到 JSON 文件，自动更新 metadata.updated。"""
        self.data.setdefault("metadata", {})
        self.data["metadata"]["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        return self.json_path

    # ── 初始化 ─────────────────────────────────────────

    def init(self, title: str, description: str = "", md_file: str = "") -> dict:
        """创建空路线图，带一个 root 节点。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.data = {
            "title": title,
            "description": description,
            "version": 1,
            "nodes": {
                "1": {
                    "id": "1",
                    "label": title,
                    "status": STATUS_IN_PROGRESS,
                    "mode": MODE_EXPLORE,
                    "parent": None,
                    "children": [],
                    "decisions": [],
                    "notes": "",
                }
            },
            "metadata": {
                "created": now,
                "updated": now,
                "md_file": md_file,
            },
        }
        return self.data

    # ── 节点 CRUD ──────────────────────────────────────

    def add_node(
        self, parent_id: str, label: str, status: str = STATUS_PENDING, mode: str = MODE_EXPLORE
    ) -> dict:
        """在父节点下添加子节点。返回新节点。"""
        if parent_id not in self.data["nodes"]:
            raise KeyError(f"父节点不存在: {parent_id}")

        index = next_child_index(self.data, parent_id)
        node_id = gen_child_id(parent_id, index)

        node = {
            "id": node_id,
            "label": label,
            "status": status,
            "mode": mode,
            "parent": parent_id,
            "children": [],
            "decisions": [],
            "notes": "",
        }

        self.data["nodes"][node_id] = node
        self.data["nodes"][parent_id]["children"].append(node_id)

        self._sync_parent_status(node_id)

        return node

    def update_node(
        self,
        node_id: str,
        label: Optional[str] = None,
        status: Optional[str] = None,
        mode: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """更新节点的属性。只更新传入的非 None 字段。"""
        if node_id not in self.data["nodes"]:
            raise KeyError(f"节点不存在: {node_id}")

        node = self.data["nodes"][node_id]
        if label is not None:
            node["label"] = label
        if status is not None:
            if status not in (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_BLOCKED):
                raise ValueError(f"无效状态: {status}")
            node["status"] = status
        if mode is not None:
            if mode not in (MODE_EXPLORE, MODE_EXPLOIT):
                raise ValueError(f"无效模式: {mode}")
            node["mode"] = mode
        if notes is not None:
            node["notes"] = notes

        self._sync_parent_status(node_id)

        return node

    def delete_node(self, node_id: str) -> list[str]:
        """删除节点及其所有子节点。返回被删除的 id 列表。"""
        if node_id not in self.data["nodes"]:
            raise KeyError(f"节点不存在: {node_id}")
        if node_id == "1":
            raise ValueError("不能删除根节点")

        # 递归收集所有子孙节点
        deleted = []

        def _collect(nid):
            node = self.data["nodes"].get(nid)
            if not node:
                return
            for cid in list(node["children"]):
                _collect(cid)
            deleted.append(nid)

        _collect(node_id)

        # 从父节点的 children 中移除
        parent_id = self.data["nodes"][node_id]["parent"]
        if parent_id and parent_id in self.data["nodes"]:
            self.data["nodes"][parent_id]["children"].remove(node_id)

        # 删除节点
        for nid in deleted:
            del self.data["nodes"][nid]

        self._sync_parent_status(node_id)

        return deleted

    def get_node(self, node_id: str) -> dict:
        """获取节点。"""
        if node_id not in self.data["nodes"]:
            raise KeyError(f"节点不存在: {node_id}")
        return self.data["nodes"][node_id]

    # ── 决策 ───────────────────────────────────────────

    def add_decision(self, node_id: str, question: str, answer: str, note: str = "") -> dict:
        """为节点添加决策记录。"""
        node = self.get_node(node_id)
        decision = {"q": question, "answer": answer, "note": note}
        node["decisions"].append(decision)
        return decision

    def get_decisions(self, node_id: Optional[str] = None) -> list:
        """获取决策记录。无 node_id 则返回全部。"""
        if node_id:
            return self.get_node(node_id)["decisions"]
        result = []
        for nid, node in self.data["nodes"].items():
            for d in node["decisions"]:
                result.append({"node_id": nid, "node_label": node["label"], **d})
        return result

    # ── 树遍历 ─────────────────────────────────────────

    def get_tree(self, root_id: str = "1", max_depth: int = 10) -> str:
        """生成 Unicode 盒状树形文本视图。"""
        if root_id not in self.data["nodes"]:
            return f"(节点 {root_id} 不存在)"

        lines = []

        def _render(nid: str, prefix: str, is_last: bool, depth: int):
            if depth > max_depth:
                return
            node = self.data["nodes"].get(nid)
            if not node:
                return

            icon = STATUS_ICONS.get(node["status"], "[?]")
            mode_tag = MODE_TAG.get(node.get("mode"), "")
            connector = "└── " if is_last else "├── "
            line = f"{prefix}{connector}{icon}{mode_tag} {nid}. {node['label']}"
            lines.append(line)

            children = node.get("children", [])
            for i, cid in enumerate(children):
                child_is_last = (i == len(children) - 1)
                child_prefix = prefix + ("    " if is_last else "│   ")
                _render(cid, child_prefix, child_is_last, depth + 1)

        if root_id in self.data["nodes"]:
            root = self.data["nodes"][root_id]
            icon = STATUS_ICONS.get(root["status"], "[?]")
            mode_tag = MODE_TAG.get(root.get("mode"), "")
            lines.append(f"{icon}{mode_tag} {root_id}. {root['label']}")
            children = root.get("children", [])
            for i, cid in enumerate(children):
                child_is_last = (i == len(children) - 1)
                _render(cid, "", child_is_last, 1)

        return "\n".join(lines)

    def get_path(self, node_id: str) -> list[str]:
        """获取从根到目标节点的路径（id 列表）。"""
        path = []
        current = node_id
        while current:
            path.insert(0, current)
            current = self.data["nodes"][current]["parent"]
        return path

    def get_siblings(self, node_id: str) -> list[str]:
        """获取兄弟节点 id 列表（不含自身）。"""
        node = self.get_node(node_id)
        parent_id = node["parent"]
        if not parent_id:
            return []
        parent = self.data["nodes"][parent_id]
        return [cid for cid in parent["children"] if cid != node_id]

    def get_current_focus(self) -> Optional[str]:
        """找到第一个 in_progress 的叶子节点作为当前施工点。"""
        for nid, node in self.data["nodes"].items():
            if node["status"] == STATUS_IN_PROGRESS and not node["children"]:
                return nid
        return None

    def _sync_parent_status(self, node_id: str):
        """自底向上级联同步父节点状态。

        规则：
        - 全部子节点 completed → 父节点 = completed
        - 任一子节点非 completed → 父节点 ≠ completed（降为 in_progress）
        """
        current = self.data["nodes"].get(node_id)
        if not current:
            return
        parent_id = current.get("parent")
        while parent_id and parent_id in self.data["nodes"]:
            parent = self.data["nodes"][parent_id]
            children = parent.get("children", [])
            if not children:
                break
            all_done = all(
                self.data["nodes"][cid]["status"] == STATUS_COMPLETED
                for cid in children if cid in self.data["nodes"]
            )
            if all_done:
                parent["status"] = STATUS_COMPLETED
            elif parent["status"] == STATUS_COMPLETED:
                parent["status"] = STATUS_IN_PROGRESS
            parent_id = parent.get("parent")

    # ── Markdown 渲染 ──────────────────────────────────

    def render_full_section(self) -> str:
        """全量渲染（调试用）：全展开树 + 全部决策表 + 焦点详情。"""
        now = self.data["metadata"].get("updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        focus_id = self.get_current_focus()
        focus_line = ""
        if focus_id:
            focus_node = self.data["nodes"][focus_id]
            focus_line = f"> 当前施工: {focus_id}. {focus_node['label']}"

        tree_text = self.get_tree(max_depth=50)

        all_decisions = self.get_decisions()
        decision_lines = ""
        if all_decisions:
            decision_lines = "| 节点 | 问题 | 答案 | 备注 |\n"
            decision_lines += "|------|------|------|------|\n"
            for d in all_decisions:
                note = d.get("note", "")
                decision_lines += f"| {d['node_id']} | {d['q']} | {d['answer']} | {note} |\n"

        current_detail = ""
        if focus_id:
            current_detail = f"\n### 当前施工点\n\n**{focus_id}. {self.data['nodes'][focus_id]['label']}**\n"
            if self.data["nodes"][focus_id].get("notes"):
                current_detail += f"\n{self.data['nodes'][focus_id]['notes']}\n"

        section = f"""## ZJ Roadmap

> 数据文件: `{os.path.basename(self.json_path)}` | 最后更新: {now}
{focus_line}

<!-- ROADMAP_TREE_START -->
<!-- 由 zj-roadmap-driven 自动生成，请勿手动编辑 -->
{tree_text}
<!-- ROADMAP_TREE_END -->
"""
        if decision_lines:
            section += f"\n### 决策历史\n\n{decision_lines}\n"

        if current_detail:
            section += current_detail

        return section

    def render_light_section(self) -> str:
        """轻量渲染（Human 视图）：树 depth=2 + 焦点节点展开。"""
        now = self.data["metadata"].get("updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        tree_text = self.get_tree(max_depth=2)

        focus_id = self.get_current_focus()
        focus_detail = ""
        if focus_id:
            focus_node = self.data["nodes"][focus_id]
            focus_detail = f"\n### 当前施工：{focus_id}. {focus_node['label']}\n"
            if focus_node.get("notes"):
                focus_detail += f"\n{focus_node['notes']}\n"
            decisions = focus_node.get("decisions", [])
            if decisions:
                focus_detail += "\n**决策：**\n"
                for d in decisions:
                    note = f" ({d.get('note', '')})" if d.get("note") else ""
                    focus_detail += f"- Q: {d['q']} → {d['answer']}{note}\n"

        section = f"""<!-- ROADMAP_SECTION_START -->
## ZJ Roadmap

> 数据文件: `{os.path.basename(self.json_path)}` | 最后更新: {now}

{tree_text}
<!-- ROADMAP_SECTION_END -->
"""
        if focus_detail:
            section += focus_detail

        return section

    def write_markdown_section(self) -> Optional[str]:
        """将 ZJ Roadmap section 写入关联的 md 文件。

        在 md 文件中查找 `## ZJ Roadmap` section 并替换，
        不存在则追加到文件末尾。
        返回写入的文件路径，无关联 md 文件则返回 None。
        """
        md_file = self.data.get("metadata", {}).get("md_file", "")
        if not md_file:
            return None

        section = self.render_light_section()

        if os.path.exists(md_file):
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 查找并替换已有的 section
            marker = "## ZJ Roadmap"
            next_marker = "\n## "
            idx = content.find(marker)
            if idx >= 0:
                # 找到下一个 ## section 或文件末尾
                end = content.find(next_marker, idx + len(marker))
                if end < 0:
                    end = len(content)
                content = content[:idx] + section + content[end:]
            else:
                content = content.rstrip() + "\n\n" + section
        else:
            content = section

        os.makedirs(os.path.dirname(md_file), exist_ok=True)
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(content)

        return md_file

    def link_md_file(self, md_file: str):
        """关联一个 md 文件。"""
        self.data.setdefault("metadata", {})
        self.data["metadata"]["md_file"] = os.path.abspath(md_file)

    # ── 验证 ───────────────────────────────────────────

    def validate(self) -> list[str]:
        """验证路线图数据完整性，返回错误列表。"""
        errors = []

        # 必须有根节点
        if "1" not in self.data.get("nodes", {}):
            errors.append("缺少根节点 '1'")

        for nid, node in self.data.get("nodes", {}).items():
            # id 一致性
            if node.get("id") != nid:
                errors.append(f"节点 {nid}: id 字段不一致 ({node.get('id')})")

            # parent 引用有效性
            parent = node.get("parent")
            if parent is not None:
                if parent not in self.data["nodes"]:
                    errors.append(f"节点 {nid}: 父节点 {parent} 不存在")
                elif nid not in self.data["nodes"][parent].get("children", []):
                    errors.append(f"节点 {nid}: 父节点 {parent} 的 children 列表中缺少此节点")

            # children 引用有效性
            for cid in node.get("children", []):
                if cid not in self.data["nodes"]:
                    errors.append(f"节点 {nid}: 子节点 {cid} 不存在")
                elif self.data["nodes"][cid].get("parent") != nid:
                    errors.append(f"节点 {nid}: 子节点 {cid} 的 parent 指向不一致")

            # 状态合法性
            if node.get("status") not in (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_BLOCKED):
                errors.append(f"节点 {nid}: 无效状态 '{node.get('status')}'")

        return errors

    # ── 统计 ───────────────────────────────────────────

    def stats(self) -> dict:
        """路线图统计信息。"""
        nodes = self.data.get("nodes", {})
        status_counts = {
            STATUS_PENDING: 0,
            STATUS_IN_PROGRESS: 0,
            STATUS_COMPLETED: 0,
            STATUS_BLOCKED: 0,
        }
        for n in nodes.values():
            s = n.get("status", STATUS_PENDING)
            if s in status_counts:
                status_counts[s] += 1

        total_decisions = sum(len(n.get("decisions", [])) for n in nodes.values())

        return {
            "total_nodes": len(nodes),
            "status_counts": status_counts,
            "total_decisions": total_decisions,
            "max_depth": max((node_depth(nid) for nid in nodes), default=0),
        }
