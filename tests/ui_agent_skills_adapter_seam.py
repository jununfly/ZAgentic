"""Adapter invocation seam — 1-7-5 测试主体的分层原语（roadmap 1-7-5 预置基建）。

解决的问题
----------
原风险项：「测试主体受限——仅 Storybook 离线可用；json-render/A2UI 无运行时
投影引擎 → 断网/远程只能走契约级注入」。

根因是**把「被测对象」和「故障来源」混为一谈**：

* 1-7-5 的被测对象是 **边界编排层**——「adapter 报 X 类故障 → boundary 执行 Y
  回退 → 本地恢复不变量仍成立」。这是一条**接口上的决策性质**，与 adapter 自身
  有没有运行时**正交**。
* 故障从哪来不重要，重要的是故障被**归类正确**。归类发生在 seam 上。

所以「只有 Storybook 有运行时」不是障碍，而是**资产**：Storybook 的真实运行时
用来校验 seam 的保真度（fidelity），没有运行时的 adapter 根本不该进 invocation
测试面。真正会犯错的两条路是：(a) 试图给 json-render/A2UI 造运行时（越界）；
(b) 把整个回退矩阵降级成「契约级断言」（丢掉机器证据）。

三层测试主体
------------
* **L1 真实运行时**：Storybook，经 ``RealAdapterSeam`` 适配到 seam。产出真实
  成功证据，并为保真度断言提供基准。
* **L2 可编程故障注入**：``SimulatedAdapterSeam``，实现同一 seam，可编程产出
  四类 outcome。用于穷举回退矩阵（3 类故障 × 四态生命周期）。
* **L3 无运行时**：json-render / A2UI，在 invocation-surface 索引里声明
  ``invocation_surface: none``，**显式排除**出 invocation/回退执行测试面，只参与
  lifecycle + removal R1–R5 + manifest 契约测试。排除必须是声明式且被断言的，
  不允许静默 skip。

诚实的局限（不支持的声称）
--------------------------
Storybook adapter 是**离线确定性**的，本仓库**无法真实观测** network_loss /
remote_failure。这两类是 seam 契约定义，不是真实运行时证据。
``REAL_RUNTIME_BACKED`` / ``SEAM_CONTRACT_ONLY`` 把这个边界写死在代码里，任何
测试不得声称「真实断网已验证」。
"""
from __future__ import annotations

import copy
import json
import pathlib
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

REPO = pathlib.Path(__file__).resolve().parents[1]
SURFACE_INDEX_PATH = (
    REPO / "tests/ui-agent-skills/fixtures/adapters/registry/invocation-surface.json"
)

# --------------------------------------------------------------------------
# Outcome classes — 严格对应 adapter-boundary-v1.md §6.2 的三类故障 + 成功
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

#: outcome class -> 管辖它的 manifest fallback 键（§6.2）。ok 无回退键。
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

#: 四态生命周期（§6.1）。注意：这是 adapter 级，与 receipt 级 QUARANTINED 无关，
#: 辨析见 docs/plans/adapter-boundary-v1/quarantine-disambiguation.md。
VALID_LIFECYCLE: Tuple[str, ...] = ("active", "degraded", "disabled", "quarantine")

#: 诚实账本：哪些 outcome class 在本仓库有真实运行时观测支撑。
REAL_RUNTIME_BACKED = frozenset({OUTCOME_OK, OUTCOME_FAILURE})
#: 其余为 seam 契约定义，无真实运行时证据——不得声称已真实验证。
SEAM_CONTRACT_ONLY: Tuple[str, ...] = tuple(
    c for c in OUTCOME_CLASSES if c not in REAL_RUNTIME_BACKED
)

#: 异常归类为网络类的启发式标记（仅用于 RealAdapterSeam 的异常分类）。
NETWORK_ERROR_MARKERS: Tuple[str, ...] = (
    "socket", "ssl", "urllib", "http", "requests", "httpx",
    "connection", "timeout", "dns", "network",
)

#: 本地恢复不变量（§6.2）要求这三项在任何回退后仍可用。
LOCAL_RECOVERY_SURFACES: Tuple[str, ...] = (
    "canonical", "static_preview", "local_verify",
)


# --------------------------------------------------------------------------
# Outcome
# --------------------------------------------------------------------------
class AdapterOutcome:
    """Boundary 对一次 adapter 调用所能看到的全部信息。

    ``outcome_class`` 是 **seam 级**（调用是否完成）；``receipt_status`` 是
    **receipt 级**（这次证据是否可信）。二者正交：seam 成功（ok）完全可能携带
    ``QUARANTINED`` receipt。刻意不把 receipt 的 QUARANTINED 折叠进
    outcome_class——那正是 quarantine 消歧要防的混淆。
    """

    __slots__ = ("adapter_id", "outcome_class", "envelope", "receipt_status", "error")

    def __init__(
        self,
        adapter_id: str,
        outcome_class: str,
        *,
        envelope: "Optional[Dict[str, Any]]" = None,
        receipt_status: "Optional[str]" = None,
        error: "Optional[str]" = None,
    ) -> None:
        if outcome_class not in OUTCOME_CLASSES:
            raise ValueError(
                f"invalid outcome_class {outcome_class!r}; expected one of {OUTCOME_CLASSES}"
            )
        self.adapter_id = adapter_id
        self.outcome_class = outcome_class
        self.envelope = envelope
        self.receipt_status = receipt_status
        self.error = error

    @property
    def ok(self) -> bool:
        return self.outcome_class == OUTCOME_OK

    @property
    def fallback_key(self) -> "Optional[str]":
        """管辖本次 outcome 的 manifest fallback 键；成功调用无回退键。"""
        return FALLBACK_KEY.get(self.outcome_class)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "outcome_class": self.outcome_class,
            "receipt_status": self.receipt_status,
            "error": self.error,
            "has_envelope": self.envelope is not None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"AdapterOutcome({self.adapter_id}, {self.outcome_class}, receipt={self.receipt_status})"


def classify_exception(exc: BaseException) -> str:
    """把异常归类到 outcome class。启发式，仅用于真实 driver 的兜底分类。"""
    name = f"{type(exc).__module__}.{type(exc).__name__}".lower()
    if any(marker in name for marker in NETWORK_ERROR_MARKERS):
        return OUTCOME_NETWORK_LOSS
    return OUTCOME_FAILURE


# --------------------------------------------------------------------------
# L1 — 真实运行时 seam
# --------------------------------------------------------------------------
class RealAdapterSeam:
    """把真实 adapter（如 storybook_adapter.run）适配到 seam。

    ``runner`` 是可调用对象 ``(request) -> envelope dict``。真实 adapter 抛异常
    时按 :func:`classify_exception` 归类；正常返回一律 ``OUTCOME_OK``，receipt
    状态原样透传（不做折叠）。
    """

    def __init__(self, adapter_id: str, runner: Callable[[dict], dict]) -> None:
        self.adapter_id = adapter_id
        self._runner = runner
        self.calls: List[dict] = []

    def invoke(self, request: dict) -> AdapterOutcome:
        self.calls.append(copy.deepcopy(request))
        try:
            envelope = self._runner(request)
        except Exception as exc:  # noqa: BLE001 - seam 必须收敛任何异常
            return AdapterOutcome(
                self.adapter_id,
                classify_exception(exc),
                error=f"{type(exc).__name__}: {exc}",
            )
        status = envelope.get("status") if isinstance(envelope, dict) else None
        return AdapterOutcome(
            self.adapter_id, OUTCOME_OK, envelope=envelope, receipt_status=status
        )


# --------------------------------------------------------------------------
# L2 — 可编程故障注入 seam
# --------------------------------------------------------------------------
def default_simulated_envelope(adapter_id: str, receipt_status: str = "OK") -> Dict[str, Any]:
    """Simulated seam 的成功包络。key set 与类型必须与真实 Storybook adapter 的
    成功包络一致，否则 :func:`assert_seam_fidelity` 会失败——这是防「假 adapter
    自说自话」的核心护栏。"""
    return {
        "adapter_id": adapter_id,
        "engine": "simulated",
        "status": receipt_status,
        "stories": ["login::idle"],
        "checks": [
            {
                "dimension": "stories",
                "claim": "simulated claim",
                "threshold": "simulated threshold",
                "command": "simulated --check",
                "commit": "rev-simulated",
                "fixture_hash": "0" * 64,
                "env_hash": "0" * 64,
                "artifact": "ui-flow:rev-simulated",
                "status": "PASS",
                "evidence_new": True,
            }
        ],
        "receipt": {"status": receipt_status, "checked": 1},
        "report": {"stories": ["login::idle"]},
    }


class SimulatedAdapterSeam:
    """可编程故障注入：实现同一 seam，按 ``outcome`` 产出分类好的 outcome。

    用于穷举回退矩阵。它的**保真度不由自己证明**，而由
    :func:`assert_seam_fidelity` 对真实 Storybook 包络做形状比对来证明。
    """

    def __init__(
        self,
        adapter_id: str,
        *,
        outcome: str = OUTCOME_OK,
        receipt_status: "Optional[str]" = "OK",
        envelope: "Optional[Dict[str, Any]]" = None,
        error: "Optional[str]" = None,
    ) -> None:
        if outcome not in OUTCOME_CLASSES:
            raise ValueError(
                f"invalid outcome {outcome!r}; expected one of {OUTCOME_CLASSES}"
            )
        self.adapter_id = adapter_id
        self._outcome = outcome
        self._receipt_status = receipt_status
        self._envelope = envelope
        self._error = error
        self.calls: List[dict] = []

    def invoke(self, request: dict) -> AdapterOutcome:
        self.calls.append(copy.deepcopy(request))
        if self._outcome == OUTCOME_OK:
            envelope = self._envelope or default_simulated_envelope(
                self.adapter_id, self._receipt_status or "OK"
            )
            return AdapterOutcome(
                self.adapter_id,
                OUTCOME_OK,
                envelope=copy.deepcopy(envelope),
                receipt_status=self._receipt_status,
            )
        return AdapterOutcome(
            self.adapter_id,
            self._outcome,
            error=self._error or f"simulated {self._outcome}",
        )


# --------------------------------------------------------------------------
# 保真度护栏
# --------------------------------------------------------------------------
def envelope_shape(envelope: "Optional[Dict[str, Any]]") -> Dict[str, str]:
    """包络的形状指纹：``{key: type_name}``。用于形状比对而非值比对。"""
    if not isinstance(envelope, dict):
        return {}
    return {key: type(value).__name__ for key, value in sorted(envelope.items())}


def assert_seam_fidelity(
    real_envelope: Dict[str, Any], simulated_envelope: Dict[str, Any]
) -> None:
    """断言 simulated 包络与真实包络形状一致（key set + 值类型）。

    这是 L2 故障注入可信的前提：如果 simulated 的成功包络连形状都跟真 adapter
    不一样，它注入的故障就没有意义。
    """
    real = envelope_shape(real_envelope)
    sim = envelope_shape(simulated_envelope)
    if real != sim:
        only_real = sorted(set(real) - set(sim))
        only_sim = sorted(set(sim) - set(real))
        differ = sorted(k for k in set(real) & set(sim) if real[k] != sim[k])
        raise AssertionError(
            "seam fidelity failed: simulated envelope shape != real envelope shape; "
            f"only_real={only_real}; only_sim={only_sim}; type_diff={differ}"
        )


# --------------------------------------------------------------------------
# 调用面索引（deny-first）
# --------------------------------------------------------------------------
def load_invocation_surface_index(
    path: "pathlib.Path | str | None" = None,
) -> Dict[str, Any]:
    target = pathlib.Path(path) if path is not None else SURFACE_INDEX_PATH
    raw = json.loads(target.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def assert_invocation_surface_declared(
    registry_ids, index: "Optional[Dict[str, Any]]" = None
) -> None:
    """deny-first：registry 里每个 adapter 都必须在索引中声明调用面。

    未声明 = 报错（不是静默跳过）。这样新增 adapter 时会强制回答
    「它有没有运行时」，避免无运行时 adapter 混进 invocation 测试面。
    """
    idx = index if index is not None else load_invocation_surface_index()
    missing = sorted(set(registry_ids) - set(idx))
    if missing:
        raise AssertionError(
            "adapters without a declared invocation surface: "
            f"{missing}; declare them in {SURFACE_INDEX_PATH.name}"
        )
    for adapter_id in sorted(set(registry_ids)):
        surface = idx[adapter_id].get("invocation_surface")
        if surface not in ("runtime", "none"):
            raise AssertionError(
                f"adapter {adapter_id}: invocation_surface must be 'runtime' or "
                f"'none', got {surface!r}"
            )
        if not idx[adapter_id].get("reason"):
            raise AssertionError(
                f"adapter {adapter_id}: invocation surface declaration needs a 'reason'"
            )


def runtime_capable_ids(index: "Optional[Dict[str, Any]]" = None) -> List[str]:
    idx = index if index is not None else load_invocation_surface_index()
    return sorted(k for k, v in idx.items() if v.get("invocation_surface") == "runtime")


def no_runtime_ids(index: "Optional[Dict[str, Any]]" = None) -> List[str]:
    idx = index if index is not None else load_invocation_surface_index()
    return sorted(k for k, v in idx.items() if v.get("invocation_surface") == "none")


# --------------------------------------------------------------------------
# 回退矩阵 + 本地恢复不变量
# --------------------------------------------------------------------------
def iter_fallback_matrix(
    outcomes=OUTCOME_CLASSES, lifecycles=VALID_LIFECYCLE
) -> Iterator[Tuple[str, str]]:
    """产出 (outcome_class, lifecycle) 全组合，供回退矩阵测试遍历。

    调用方**必须**断言迭代次数 > 0：空矩阵会让门禁循环零次迭代却返回 PASS，
    是最难发现的假绿。
    """
    for outcome in outcomes:
        for lifecycle in lifecycles:
            yield (outcome, lifecycle)


def expected_fallback_action(manifest: Dict[str, Any], outcome_class: str) -> str:
    """按 §6.2 取某 outcome 应执行的回退动作。成功调用无回退动作。"""
    key = FALLBACK_KEY.get(outcome_class)
    if key is None:
        raise ValueError(f"outcome {outcome_class!r} has no fallback action (success path)")
    fallback = manifest.get("fallback") or {}
    if key not in fallback:
        raise KeyError(f"manifest {manifest.get('id')} missing fallback key {key!r}")
    action = fallback[key]
    if action not in FALLBACK_ACTIONS:
        raise ValueError(
            f"manifest {manifest.get('id')}: fallback {key}={action!r} not in {FALLBACK_ACTIONS}"
        )
    return action


class CapabilitySnapshot:
    """回退执行后 boundary 暴露的能力面，用于断言本地恢复不变量（§6.2）。"""

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
    """断言本地恢复不变量：三项能力面均可用 + resolver 不崩溃（success 或 degraded）。

    对应 §7 的 R1/R2/R3/R5。任何回退执行完都必须过这一条。
    """
    missing = [
        surface
        for surface in ("canonical", "static_preview", "local_verify")
        if not getattr(snapshot, surface)
    ]
    if missing:
        raise AssertionError(
            f"local recovery invariant violated: unavailable surfaces {missing}"
        )
    if snapshot.resolver_status not in ("success", "degraded"):
        raise AssertionError(
            "R5 violated: resolver must resolve or report degraded, got "
            f"{snapshot.resolver_status!r}"
        )
