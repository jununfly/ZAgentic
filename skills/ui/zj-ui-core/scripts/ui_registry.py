"""Ten-skill capability manifest registry for the `zj-ui-*` chain (S1..S10).

This is the machine-readable form of `ui-agent-skills-skill-capability-manifest.md`
§3 (roadmap node 1-3-1). Every skill carries the full 16-field manifest so the
resolver's static checks (resolver-contract.md §2) can run against it. The
registry is read-only data: the resolver never mutates it, and a malformed entry
is dropped by `registry_static_check`, never silently repaired.

Pipeline order is the dependency order the orchestrator walks:

    brief -> discover -> direction -> design_system -> flow -> prototype
          -> visual_review -> break -> verify -> handoff

`zj-ui-core` (S0) is intentionally absent: it is the base carrier and has no
stage in the chain.
"""

from __future__ import annotations

# The 16 fields each manifest must carry. Missing any of them -> the skill is
# excluded from the registry (resolver-contract.md §2.3).
MANIFEST_FIELDS = (
    "skill_id",
    "manifest_version",
    "stage",
    "owner_scope",
    "writes",
    "reads",
    "input",
    "output",
    "forbidden",
    "dependencies",
    "required_capabilities",
    "stop_conditions",
    "owner",
    "precedence",
    "failure_fixtures",
    "human_gate",
)

# Pipeline order used by the orchestrator (ui_chain.py).
CHAIN_ORDER = (
    "brief",
    "discover",
    "direction",
    "design_system",
    "flow",
    "prototype",
    "visual_review",
    "break",
    "verify",
    "handoff",
)

MANIFESTS = [
    {
        "skill_id": "zj-ui-brief",
        "manifest_version": "0.1.0",
        "stage": "brief",
        "owner_scope": "write",
        "writes": ["UI-BRIEF.md"],
        "reads": [],
        "input": [
            {"name": "用户对话或 UI-BRIEF.md 编辑", "type": "text", "required": "yes", "source": "agent"},
            {"name": "现有 artifact 版本", "type": "revision", "required": "no", "source": "store"},
        ],
        "output": [
            {"name": "UI-BRIEF.md draft", "type": "object", "artifact_kind": "UI-BRIEF.md", "atomic": True},
            {"name": "unknown[]", "type": "list", "artifact_kind": "UI-BRIEF.md", "atomic": False},
        ],
        "forbidden": [
            "执行 effect（代码执行/网络/凭据/写回）",
            "替用户编造 goal_users/success_criteria",
            "把 unknown 压成空值",
            "连续追问超过 2 个问题",
        ],
        "dependencies": ["sub-01 brief schema", "上游对话/文档 input_revision"],
        "required_capabilities": ["document_parse", "schema_validate"],
        "stop_conditions": [
            {"condition": "缺目标/用户/成功标准", "action": "WAIT_HUMAN", "next": "NEEDS_CONTEXT"},
            {"condition": "schema 校验失败", "action": "STOP", "next": "REJECTED"},
        ],
        "owner": "brief/contract owner",
        "precedence": 10,
        "failure_fixtures": ["FF-BRIEF-01", "FF-BRIEF-02", "FF-BRIEF-03"],
        "human_gate": "conditional",
    },
    {
        "skill_id": "zj-ui-discover",
        "manifest_version": "0.1.0",
        "stage": "discover",
        "owner_scope": "write",
        "writes": ["UI-BRIEF.md"],
        "reads": ["UI-BRIEF.md"],
        "input": [
            {"name": "UI-BRIEF.md draft", "type": "revision", "required": "yes", "source": "store"},
            {"name": "追问预算", "type": "int", "required": "yes", "source": "agent"},
        ],
        "output": [
            {"name": "问题清单", "type": "list", "artifact_kind": "non-canonical", "atomic": False},
            {"name": "unknown[] 条目", "type": "list", "artifact_kind": "UI-BRIEF.md", "atomic": True},
        ],
        "forbidden": [
            "替用户做审美/业务决定",
            "把证据不足写成已证实",
            "追问超过 2 次",
            "改写 S1 已冻结的必填字段值",
        ],
        "dependencies": ["S1 通过的 revision"],
        "required_capabilities": ["evidence_grading"],
        "stop_conditions": [
            {"condition": "追问用尽仍不足", "action": "WAIT_HUMAN", "next": "NEEDS_CONTEXT"},
        ],
        "owner": "brief/contract owner",
        "precedence": 20,
        "failure_fixtures": ["FF-DISC-01", "FF-DISC-02", "FF-DISC-03"],
        "human_gate": "conditional",
    },
    {
        "skill_id": "zj-ui-direction",
        "manifest_version": "0.1.0",
        "stage": "direction",
        "owner_scope": "write",
        "writes": ["UI-DESIGN.md"],
        "reads": ["UI-BRIEF.md"],
        "input": [
            {"name": "UI-BRIEF.md", "type": "revision", "required": "yes", "source": "store"},
            {"name": "方向卡", "type": "list", "required": "yes", "source": "agent"},
        ],
        "output": [
            {"name": "方向卡", "type": "list", "artifact_kind": "non-canonical", "atomic": False},
            {"name": "direction_choice 候选", "type": "object", "artifact_kind": "UI-DESIGN.md", "atomic": True},
        ],
        "forbidden": [
            "自动替用户选定方向",
            "套用未注明来源的模板",
            "方向不唯一时默认取第一个",
            "把外部方法主体并入本 skill",
        ],
        "dependencies": ["S2 revision", "外部参考 provenance（license/source 必填）"],
        "required_capabilities": ["direction_card_gen", "provenance_register"],
        "stop_conditions": [
            {"condition": "方向不唯一或缺来源", "action": "WAIT_HUMAN", "next": "HUMAN_REVIEW_REQUIRED"},
            {"condition": "来源 license unknown", "action": "STOP", "next": "QUARANTINED"},
        ],
        "owner": "direction/design owner",
        "precedence": 30,
        "failure_fixtures": ["FF-DIR-01", "FF-DIR-02", "FF-DIR-03"],
        "human_gate": "required",
    },
    {
        "skill_id": "zj-ui-design-system",
        "manifest_version": "0.1.0",
        "stage": "design_system",
        "owner_scope": "write",
        "writes": ["UI-DESIGN.md"],
        "reads": ["UI-DESIGN.md", "UI-BRIEF.md"],
        "input": [
            {"name": "UI-DESIGN.md 方向选择", "type": "revision", "required": "yes", "source": "store"},
            {"name": "token/catalog 草案", "type": "object", "required": "yes", "source": "agent"},
        ],
        "output": [
            {"name": "tokens", "type": "object", "artifact_kind": "UI-DESIGN.md", "atomic": True},
            {"name": "component catalog", "type": "list", "artifact_kind": "UI-DESIGN.md", "atomic": False},
        ],
        "forbidden": [
            "注册未声明来源的组件",
            "输出 contrast 不达标的配色",
            "合并外部 runtime",
            "让 adapter 拥有 catalog 字段值",
        ],
        "dependencies": ["S3 Human 选择", "sub-01 design schema", "字体 license 台账"],
        "required_capabilities": ["contrast_compute", "component_registry"],
        "stop_conditions": [
            {"condition": "未注册组件 / contrast 不达标", "action": "STOP", "next": "BLOCKED"},
            {"condition": "font license unknown", "action": "STOP", "next": "QUARANTINED"},
        ],
        "owner": "direction/design owner",
        "precedence": 40,
        "failure_fixtures": ["FF-DS-01", "FF-DS-02", "FF-DS-03"],
        "human_gate": "none",
    },
    {
        "skill_id": "zj-ui-flow",
        "manifest_version": "0.1.0",
        "stage": "flow",
        "owner_scope": "write",
        "writes": ["ui-flow/v1"],
        "reads": ["UI-DESIGN.md", "UI-BRIEF.md"],
        "input": [
            {"name": "UI-DESIGN.md", "type": "revision", "required": "yes", "source": "store"},
            {"name": "UI-BRIEF.md", "type": "revision", "required": "yes", "source": "store"},
        ],
        "output": [
            {"name": "ui-flow/v1 六义", "type": "object", "artifact_kind": "ui-flow/v1", "atomic": True},
        ],
        "forbidden": [
            "合并六义中任意两义",
            "让协议/外部 schema 拥有 ui-flow/v1",
            "丢弃 unknown 四元组",
            "接受第二个写 owner",
        ],
        "dependencies": ["S4 revision", "ui-flow/v1 schema lock"],
        "required_capabilities": ["semantic_round_trip", "offline_replay", "migration_map"],
        "stop_conditions": [
            {"condition": "状态/动作/意图丢失、双 owner、unknown 未保留", "action": "STOP", "next": "REJECTED"},
            {"condition": "major version mismatch", "action": "STOP", "next": "BLOCKED_CONTRACT_MISMATCH"},
        ],
        "owner": "flow/schema owner",
        "precedence": 50,
        "failure_fixtures": ["FF-FLOW-01", "FF-FLOW-02", "FF-FLOW-03"],
        "human_gate": "none",
    },
    {
        "skill_id": "zj-ui-prototype",
        "manifest_version": "0.1.0",
        "stage": "prototype",
        "owner_scope": "emit",
        "writes": [],
        "reads": ["ui-flow/v1"],
        "input": [
            {"name": "ui-flow/v1", "type": "revision", "required": "yes", "source": "store"},
            {"name": "component catalog", "type": "revision", "required": "yes", "source": "store"},
            {"name": "effect intent", "type": "object", "required": "conditional", "source": "agent"},
        ],
        "output": [
            {"name": "preview / 实现切片", "type": "object", "artifact_kind": "non-canonical", "atomic": False},
        ],
        "forbidden": [
            "直接使用 catalog 外组件",
            "绕过 policy/approval/sandbox 执行 effect",
            "把 json-render 投影变成 SSOT",
            "写入 canonical artifact",
        ],
        "dependencies": ["S5 revision", "sub-04 policy→approval→sandbox lease→executor"],
        "required_capabilities": ["local_preview_runtime", "effect_intent_gen"],
        "stop_conditions": [
            {"condition": "未注册组件 / 危险 action", "action": "STOP", "next": "REJECTED"},
            {"condition": "远程不可用且无本地 fallback", "action": "STOP", "next": "HUMAN_REVIEW_REQUIRED"},
        ],
        "owner": "prototype owner",
        "precedence": 60,
        "failure_fixtures": ["FF-PROTO-01", "FF-PROTO-02", "FF-PROTO-03"],
        "human_gate": "required",
    },
    {
        "skill_id": "zj-ui-visual-review",
        "manifest_version": "0.1.0",
        "stage": "visual_review",
        "owner_scope": "write",
        "writes": ["review record"],
        "reads": ["preview"],
        "input": [
            {"name": "preview/实现切片", "type": "object", "required": "yes", "source": "agent"},
            {"name": "用户任务与风险 class", "type": "object", "required": "yes", "source": "agent"},
            {"name": "environment_fingerprint", "type": "object", "required": "yes", "source": "runtime"},
        ],
        "output": [
            {"name": "review record", "type": "object", "artifact_kind": "review record", "atomic": True},
        ],
        "forbidden": [
            "用截图通过单独宣称设计完成",
            "把无法归因的 diff 判为 PASS",
            "把 Human 未签写成已签",
        ],
        "dependencies": ["S6 产物", "浏览器 runner"],
        "required_capabilities": ["browser_inspect", "screenshot", "env_fingerprint"],
        "stop_conditions": [
            {"condition": "fingerprint 缺失 / diff 无法归因", "action": "STOP", "next": "QUARANTINED"},
            {"condition": "Human 未签", "action": "WAIT_HUMAN", "next": "HUMAN_REVIEW_REQUIRED"},
        ],
        "owner": "review owner",
        "precedence": 70,
        "failure_fixtures": ["FF-VR-01", "FF-VR-02", "FF-VR-03"],
        "human_gate": "required",
    },
    {
        "skill_id": "zj-ui-break",
        "manifest_version": "0.1.0",
        "stage": "break",
        "owner_scope": "write",
        "writes": ["verification receipt"],
        "reads": ["preview"],
        "input": [
            {"name": "preview/实现切片", "type": "object", "required": "yes", "source": "agent"},
            {"name": "fixture matrix", "type": "object", "required": "yes", "source": "fixture_manifest"},
            {"name": "viewport 390/768/1440", "type": "list", "required": "yes", "source": "fixture_manifest"},
        ],
        "output": [
            {"name": "verification receipt (break cell)", "type": "object", "artifact_kind": "verification receipt", "atomic": True},
        ],
        "forbidden": [
            "降低 viewport/locale 覆盖率以通过",
            "把 overflow/focus/恢复失败记为 warning 而非 fail",
        ],
        "dependencies": ["S7 通过的 review record", "fixture-manifest"],
        "required_capabilities": ["versioned_fixture_matrix", "responsive_runner"],
        "stop_conditions": [
            {"condition": "关键状态未覆盖 / overflow / focus / 恢复失败", "action": "STOP", "next": "BLOCKED"},
        ],
        "owner": "verification owner",
        "precedence": 80,
        "failure_fixtures": ["FF-BRK-01", "FF-BRK-02", "FF-BRK-03"],
        "human_gate": "none",
    },
    {
        "skill_id": "zj-ui-verify",
        "manifest_version": "0.1.0",
        "stage": "verify",
        "owner_scope": "write",
        "writes": ["verification receipt"],
        "reads": ["preview", "verification receipt"],
        "input": [
            {"name": "preview/实现切片", "type": "object", "required": "yes", "source": "agent"},
            {"name": "verification matrix", "type": "object", "required": "yes", "source": "fixture_manifest"},
            {"name": "environment_fingerprint", "type": "object", "required": "yes", "source": "runtime"},
            {"name": "oracle_version", "type": "string", "required": "yes", "source": "runtime"},
        ],
        "output": [
            {"name": "verification receipt", "type": "object", "artifact_kind": "verification receipt", "atomic": True},
            {"name": "聚合状态", "type": "enum", "artifact_kind": "verification receipt", "atomic": False},
        ],
        "forbidden": [
            "receipt 缺链路字段仍生成成功结论",
            "用 baseline 冒充新通过",
            "把 stale 基线当当前证据",
        ],
        "dependencies": ["S7、S8 完成", "Storybook active adapter（B1）"],
        "required_capabilities": ["dom_aria", "focus_check", "contrast_check", "reduced_motion", "network_boundary"],
        "stop_conditions": [
            {"condition": "visual/a11y blocker / receipt 缺链路", "action": "STOP", "next": "BLOCKED"},
            {"condition": "fingerprint 变化", "action": "STOP", "next": "HUMAN_REVIEW_REQUIRED"},
        ],
        "owner": "verification owner",
        "precedence": 90,
        "failure_fixtures": ["FF-VER-01", "FF-VER-02", "FF-VER-03"],
        "human_gate": "conditional",
    },
    {
        "skill_id": "zj-ui-handoff",
        "manifest_version": "0.1.0",
        "stage": "handoff",
        "owner_scope": "write",
        "writes": ["handoff"],
        "reads": ["verification receipt", "all canonical artifacts"],
        "input": [
            {"name": "全部 canonical artifact revision", "type": "list", "required": "yes", "source": "store"},
            {"name": "verification receipt (PASS)", "type": "object", "required": "yes", "source": "store"},
            {"name": "commit sha", "type": "string", "required": "yes", "source": "git"},
        ],
        "output": [
            {"name": "handoff", "type": "object", "artifact_kind": "handoff", "atomic": True},
        ],
        "forbidden": [
            "在 receipt 非 PASS 时产出完整 handoff",
            "省略 fallback 或 owner",
            "把外部项目链接写成唯一依赖",
        ],
        "dependencies": ["S9 status=PASS", "adapter manifest/receipt（只读）"],
        "required_capabilities": ["change_summary_gen", "repro_command_register"],
        "stop_conditions": [
            {"condition": "缺 artifact/commit/风险/owner/fallback", "action": "WAIT_HUMAN", "next": "HUMAN_REVIEW_REQUIRED"},
        ],
        "owner": "handoff owner",
        "precedence": 100,
        "failure_fixtures": ["FF-HO-01", "FF-HO-02", "FF-HO-03"],
        "human_gate": "conditional",
    },
]


def registry_static_check(registry=None):
    """resolver-contract.md §2: drop malformed entries and report why.

    Returns ``(clean, problems)`` where ``clean`` is the list of manifests that
    survive all three checks and ``problems`` is a list of human-readable
    rejection records. A registry that fails static check is not "degraded" — it
    is refused, matching the contract's "refuse to publish" wording.
    """
    registry = MANIFESTS if registry is None else registry
    problems = []
    clean = []

    for manifest in registry:
        # Check 3: every manifest must carry all 16 fields.
        missing = [field for field in MANIFEST_FIELDS if field not in manifest]
        if missing:
            problems.append(
                {"skill_id": manifest.get("skill_id", "?"), "reason": f"manifest 缺字段: {', '.join(missing)}"}
            )
            continue
        clean.append(manifest)

    # Check 1: write-owner uniqueness per (stage, artifact_kind).
    owner_count = {}
    for manifest in clean:
        if manifest["owner_scope"] != "write":
            continue
        for artifact in manifest["writes"]:
            key = (manifest["stage"], artifact)
            owner_count.setdefault(key, []).append(manifest["skill_id"])
    for (stage, artifact), owners in owner_count.items():
        if len(owners) != 1:
            problems.append(
                {
                    "skill_id": "/".join(owners),
                    "reason": f"BLOCKED_OWNER_CONFLICT: ({stage}, {artifact}) 写 owner 数={len(owners)}",
                }
            )

    # Check 2: precedence must be unique within the same stage.
    precedence_by_stage = {}
    for manifest in clean:
        precedence_by_stage.setdefault(manifest["stage"], []).append(
            (manifest["precedence"], manifest["skill_id"])
        )
    for stage, entries in precedence_by_stage.items():
        seen = {}
        for precedence, skill_id in entries:
            if precedence in seen:
                problems.append(
                    {
                        "skill_id": f"{seen[precedence]}/{skill_id}",
                        "reason": f"AMBIGUOUS: stage={stage} 内 precedence={precedence} 并列",
                    }
                )
            seen[precedence] = skill_id

    return clean, problems


def get_registry():
    """The default ten-skill registry, already passing static check."""
    clean, problems = registry_static_check(MANIFESTS)
    if problems:
        raise RuntimeError(f"default registry failed static check: {problems}")
    return clean


def precedence_version(registry):
    """sha256 of the normalized (skill_id, manifest_version, precedence) triples.

    resolver-contract.md §5.1: ``precedence_version`` is the registry-wide
    canonical hash so a precedence/manifest change changes every plan hash.
    """
    import json
    import hashlib

    triples = sorted(
        (m["skill_id"], m["manifest_version"], m["precedence"]) for m in registry
    )
    return hashlib.sha256(
        json.dumps(triples, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
