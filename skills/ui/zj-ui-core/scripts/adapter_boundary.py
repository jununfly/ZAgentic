"""AdapterBoundary v1 — 薄边界编排层（roadmap 1-7-5, a1）。

契约来源：`docs/plans/adapter-boundary-v1/adapter-boundary-v1.md`（1-7-2 定义节点）。
配套：`adapter-manifest.schema.json`（字段集）、`invocation-seam.md`（调用 seam 与
测试主体分层）、`quarantine-disambiguation.md`（术语消歧）。

Boundary **不实现渲染逻辑**，只做契约仲裁与生命周期编排（§1）：

* 四态生命周期状态机（§6.1）：`active` / `degraded` / `disabled` / `quarantine`；
  `disabled` 与 `quarantine` **永不被调用**。
* 三类故障回退分发（§6.2）：`on_failure` / `on_network_loss` / `on_remote_failure`。
* 本地恢复不变量（§6.2）：任何回退后 canonical / static-preview / local-verify
  三项仍可用，resolver 为 `success` 或 `degraded`。
* removal test 执行器（§7）：R1–R5；`removal` 是**瞬态**，不留 `removed` 状态位。

事实源约定
----------
本模块是 **outcome 分类与回退契约的唯一事实源**；`tests/ui_agent_skills_adapter_seam.py`
只提供测试 double（Real / Simulated seam）并**单向 import 本模块的常量**，避免两处
定义漂移。

本模块对 seam 只做**鸭子类型**约束：任何带 `outcome_class` / `receipt_status` 的
对象都可被消费，因此不依赖 tests/ 里的任何东西，依赖方向是单向的
（tests → production）。

诚实账本：network_loss / remote_failure 在本仓库无真实运行时观测支撑，见
`REAL_RUNTIME_BACKED` / `SEAM_CONTRACT_ONLY` 与 `invocation-seam.md`。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

# --------------------------------------------------------------------------
# Outcome 分类（唯一事实源）—— 严格对应 §6.2 三类故障 + 成功
# --------------------------------------------------------------------------
OUTCOME_OK = "ok"
OUTCOME_FAILURE = "failure"
OUTCOME_NETWORK_LOSS = "network_loss"
OUTCOME_REMOTE_FAILURE = "remote_failure"

OUTCOME_CLASSES: Tuple[str, ...] = (
    OUTCOME_OK,
    OUTCOME_FAILURE,
    OUTCOME_NETWORK_LOSS,
    OUTCOME_REMOTE_FAILURE,
)

#: outcome class -> 管辖它的 manifest fallback 键（§6.2）。成功调用无回退键。
FALLBACK_KEY: Dict[str, str] = {
    OUTCOME_FAILURE: "on_failure",
    OUTCOME_NETWORK_LOSS: "on_network_loss",
    OUTCOME_REMOTE_FAILURE: "on_remote_failure",
}

#: §6.2 允许的回退动作取值。
FALLBACK_ACTIONS: Tuple[str, ...] = (
    "static-preview",
    "local-verify",
    "degrade",
    "disable",
    "quarantine",
)

#: 回退动作中会**改变 lifecycle** 的那几个（其余只是切能力面，不动状态）。
LIFECYCLE_MUTATING_ACTIONS: Dict[str, str] = {
    "degrade": "degraded",
    "disable": "disabled",
    "quarantine": "quarantine",
}

#: 四态生命周期（§6.1）。adapter 级，与 receipt 级 QUARANTINED 无关。
VALID_LIFECYCLE: Tuple[str, ...] = ("active", "degraded", "disabled", "quarantine")

#: 可被调用的状态；`disabled` / `quarantine` 永不调用（§6.1）。
INVOCABLE_LIFECYCLE: Tuple[str, ...] = ("active", "degraded")

#: 诚实账本：哪些 outcome class 在本仓库有真实运行时观测支撑。
REAL_RUNTIME_BACKED = frozenset({OUTCOME_OK, OUTCOME_FAILURE})
SEAM_CONTRACT_ONLY: Tuple[str, ...] = tuple(
    c for c in OUTCOME_CLASSES if c not in REAL_RUNTIME_BACKED
)

#: 本地恢复不变量要求的三项能力面（§6.2 / §7 R1–R3）。
LOCAL_RECOVERY_SURFACES: Tuple[str, ...] = ("canonical", "static_preview", "local_verify")

#: removal test 五条不变量（§7）。
REMOVAL_INVARIANTS: Tuple[str, ...] = ("R1", "R2", "R3", "R4", "R5")


class BoundaryError(Exception):
    """AdapterBoundary 契约违背。一律显式抛出，不静默降级。"""


# --------------------------------------------------------------------------
# 本地恢复不变量
# --------------------------------------------------------------------------
class CapabilitySnapshot:
    """回退执行后 boundary 暴露的能力面。"""

    __slots__ = ("canonical", "static_preview", "local_verify", "resolver_status")

    def __init__(
        self,
        *,
        canonical: bool,
        static_preview: bool,
        local_verify: bool,
        resolver_status: str,
    ) -> None:
        self.canonical = canonical
        self.static_preview = static_preview
        self.local_verify = local_verify
        self.resolver_status = resolver_status

    def as_dict(self) -> Dict[str, Any]:
        return {
            "canonical": self.canonical,
            "static_preview": self.static_preview,
            "local_verify": self.local_verify,
            "resolver_status": self.resolver_status,
        }


def assert_local_recovery(snapshot: CapabilitySnapshot) -> None:
    """断言本地恢复不变量（§6.2）：三项能力面可用 + resolver 不崩溃。"""
    missing = [s for s in LOCAL_RECOVERY_SURFACES if not getattr(snapshot, s)]
    if missing:
        raise BoundaryError(
            f"local recovery invariant violated: unavailable surfaces {missing}"
        )
    if snapshot.resolver_status not in ("success", "degraded"):
        raise BoundaryError(
            f"R5 violated: resolver must resolve or report degraded, got "
            f"{snapshot.resolver_status!r}"
        )


def dispatch_fallback(manifest: Dict[str, Any], outcome_class: str) -> str:
    """按 §6.2 取某 outcome 应执行的回退动作。成功调用无回退动作。"""
    key = FALLBACK_KEY.get(outcome_class)
    if key is None:
        raise BoundaryError(
            f"outcome {outcome_class!r} has no fallback action (success path)"
        )
    fallback = manifest.get("fallback") or {}
    if key not in fallback:
        raise BoundaryError(
            f"manifest {manifest.get('id')!r} missing fallback key {key!r}"
        )
    action = fallback[key]
    if action not in FALLBACK_ACTIONS:
        raise BoundaryError(
            f"manifest {manifest.get('id')!r}: fallback {key}={action!r} "
            f"not in {FALLBACK_ACTIONS}"
        )
    return action


# --------------------------------------------------------------------------
# 边界 registry + 四态状态机
# --------------------------------------------------------------------------
class BoundaryRegistry:
    """adapter registry 的边界视图：生命周期状态机 + 调用守卫 + 回退查表。

    刻意**不持有生产 singleton**：registry 由调用方注入（测试可用可重置夹具）。
    """

    def __init__(self, manifests: Dict[str, Any]) -> None:
        if not isinstance(manifests, dict):
            raise BoundaryError(
                f"registry must be a dict (adapter_id -> manifest), got "
                f"{type(manifests).__name__}"
            )
        self._manifests: Dict[str, Any] = manifests

    # -- reads ------------------------------------------------------------
    def ids(self) -> List[str]:
        return list(self._manifests.keys())

    def has(self, adapter_id: str) -> bool:
        return adapter_id in self._manifests

    def manifest(self, adapter_id: str) -> Dict[str, Any]:
        if adapter_id not in self._manifests:
            raise BoundaryError(f"no such adapter in registry: {adapter_id}")
        return self._manifests[adapter_id]

    def lifecycle(self, adapter_id: str) -> str:
        state = self.manifest(adapter_id).get("lifecycle")
        if state not in VALID_LIFECYCLE:
            raise BoundaryError(
                f"adapter {adapter_id}: invalid lifecycle {state!r}; "
                f"expected one of {VALID_LIFECYCLE}"
            )
        return state

    # -- 状态机 ------------------------------------------------------------
    def set_lifecycle(self, adapter_id: str, state: str) -> str:
        if state not in VALID_LIFECYCLE:
            raise BoundaryError(
                f"invalid lifecycle {state!r}; expected one of {VALID_LIFECYCLE}"
            )
        self.manifest(adapter_id)["lifecycle"] = state
        return state

    def invocable(self, adapter_id: str) -> bool:
        """§6.1：`disabled` 与 `quarantine` 永不调用。"""
        return self.lifecycle(adapter_id) in INVOCABLE_LIFECYCLE

    def guard_invoke(self, adapter_id: str) -> None:
        """调用守卫：不可调用状态一律抛错，绝不静默跳过。"""
        state = self.lifecycle(adapter_id)
        if state not in INVOCABLE_LIFECYCLE:
            raise BoundaryError(
                f"adapter {adapter_id} is {state!r} and must never be invoked (§6.1)"
            )

    def apply_fallback_action(self, adapter_id: str, action: str) -> Optional[str]:
        """执行会改变 lifecycle 的回退动作，返回新状态；能力面切换返回 None。"""
        target = LIFECYCLE_MUTATING_ACTIONS.get(action)
        if target is None:
            return None
        return self.set_lifecycle(adapter_id, target)

    def fallback_for(self, adapter_id: str, outcome_class: str) -> str:
        return dispatch_fallback(self.manifest(adapter_id), outcome_class)

    # -- removal（瞬态） ---------------------------------------------------
    def remove(self, adapter_id: str) -> Dict[str, Any]:
        """瞬态删除：adapter 从 registry 消失，**不留 `removed` 状态位**（§6.1）。"""
        if adapter_id not in self._manifests:
            raise BoundaryError(f"cannot remove absent adapter: {adapter_id}")
        return self._manifests.pop(adapter_id)


# --------------------------------------------------------------------------
# 编排入口：一次 adapter 调用的完整边界决策
# --------------------------------------------------------------------------
class BoundaryDecision:
    """一次调用后 boundary 的决策记录（可审计、可断言）。"""

    __slots__ = (
        "adapter_id", "lifecycle", "invoked", "outcome_class", "receipt_status",
        "action", "reason", "error", "local_recovery",
    )

    def __init__(
        self,
        adapter_id: str,
        lifecycle: str,
        *,
        invoked: bool,
        outcome_class: "Optional[str]" = None,
        receipt_status: "Optional[str]" = None,
        action: "Optional[str]" = None,
        reason: str,
        error: "Optional[str]" = None,
        local_recovery: "Optional[Dict[str, Any]]" = None,
    ) -> None:
        self.adapter_id = adapter_id
        self.lifecycle = lifecycle
        self.invoked = invoked
        self.outcome_class = outcome_class
        self.receipt_status = receipt_status
        self.action = action
        self.reason = reason
        self.error = error
        self.local_recovery = local_recovery

    def as_dict(self) -> Dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "lifecycle": self.lifecycle,
            "invoked": self.invoked,
            "outcome_class": self.outcome_class,
            "receipt_status": self.receipt_status,
            "action": self.action,
            "reason": self.reason,
            "error": self.error,
            "local_recovery": self.local_recovery,
        }

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"BoundaryDecision({self.adapter_id}, lifecycle={self.lifecycle}, "
            f"invoked={self.invoked}, outcome={self.outcome_class}, "
            f"action={self.action}, reason={self.reason})"
        )


def invoke(
    registry: BoundaryRegistry,
    seam: Any,
    adapter_id: str,
    request: Dict[str, Any],
    *,
    capability_probe: "Optional[Callable[[str, Optional[str]], CapabilitySnapshot]]" = None,
) -> BoundaryDecision:
    """Boundary 编排入口：生命周期守卫 → 调用 → 分类 → 回退分发 → 本地恢复校验。

    参数
    ----
    seam:
        任何带 ``invoke(request)`` 且返回带 ``outcome_class`` / ``receipt_status``
        的对象（鸭子类型）。真实 adapter 与 simulated double 都可接入。
    capability_probe:
        可选，``(adapter_id, action) -> CapabilitySnapshot``。提供时在执行回退后
        强制过 :func:`assert_local_recovery`；回退后本地能力面不可用即抛错。
    """
    lifecycle = registry.lifecycle(adapter_id)

    # 1) 生命周期守卫：不可调用状态根本不发起调用（§6.1）
    if not registry.invocable(adapter_id):
        return BoundaryDecision(
            adapter_id, lifecycle, invoked=False,
            reason=f"lifecycle-not-invocable:{lifecycle}",
        )

    # 2) 调用（seam 负责把异常归类成 outcome_class）
    outcome = seam.invoke(request)
    outcome_class = getattr(outcome, "outcome_class", None)
    if outcome_class not in OUTCOME_CLASSES:
        raise BoundaryError(
            f"seam returned unknown outcome_class {outcome_class!r}; "
            f"expected one of {OUTCOME_CLASSES}"
        )

    # 3) 成功路径：不触发任何回退，receipt 状态原样透传（不折叠）
    if outcome_class == OUTCOME_OK:
        return BoundaryDecision(
            adapter_id, lifecycle, invoked=True,
            outcome_class=OUTCOME_OK,
            receipt_status=getattr(outcome, "receipt_status", None),
            reason="served",
        )

    # 4) 故障：查表取回退动作并执行
    action = registry.fallback_for(adapter_id, outcome_class)
    registry.apply_fallback_action(adapter_id, action)

    local_recovery = None
    if capability_probe is not None:
        snapshot = capability_probe(adapter_id, action)
        assert_local_recovery(snapshot)  # 回退后本地能力面必须仍在
        local_recovery = snapshot.as_dict()

    return BoundaryDecision(
        adapter_id, registry.lifecycle(adapter_id), invoked=True,
        outcome_class=outcome_class,
        receipt_status=getattr(outcome, "receipt_status", None),
        action=action,
        reason=f"fallback:{action}",
        error=getattr(outcome, "error", None),
        local_recovery=local_recovery,
    )


# --------------------------------------------------------------------------
# removal test 执行器（§7 R1–R5）
# --------------------------------------------------------------------------
class RemovalExecutor:
    """执行删除后不变量校验。

    ``probes`` 是 ``{"R1": callable(adapter_id) -> bool, ...}``，由调用方注入
    （真实环境的解析/构建/验证命令，或测试里的桩）。五条缺一即报错——
    不允许静默少测一条。

    `removal` 是瞬态：执行器只把 adapter 从 registry 移除，**不写任何 `removed`
    状态位**；执行完可校验 registry 里没有残留痕迹。
    """

    def __init__(
        self, registry: BoundaryRegistry, probes: Dict[str, Callable[[str], bool]]
    ) -> None:
        missing = [r for r in REMOVAL_INVARIANTS if r not in probes]
        if missing:
            raise BoundaryError(
                f"removal_test probes missing for {missing}; all of "
                f"{REMOVAL_INVARIANTS} are required"
            )
        self._registry = registry
        self._probes = probes

    def run(self, adapter_id: str) -> Dict[str, Any]:
        if not self._registry.has(adapter_id):
            raise BoundaryError(f"cannot test removal of absent adapter: {adapter_id}")

        removed = self._registry.remove(adapter_id)

        invariants: Dict[str, Any] = {}
        for rid in REMOVAL_INVARIANTS:
            ok = bool(self._probes[rid](adapter_id))
            invariants[rid] = {
                "id": rid,
                "ok": ok,
                "verify": ((removed.get("removal_test") or {}).get("invariants") or []),
            }

        # 瞬态性校验：registry 里不得留下 removed 状态位或僵尸条目
        residue = self._registry.has(adapter_id)
        failed = [rid for rid in REMOVAL_INVARIANTS if not invariants[rid]["ok"]]

        return {
            "adapter_id": adapter_id,
            "removed": True,
            "invariants": invariants,
            "failed": failed,
            "ok": not failed and not residue,
            "residue": residue,
        }
