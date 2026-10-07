#!/usr/bin/env python3
"""Local Codex checkpoint state and hook adapter; Python standard library only."""

import argparse
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import time
import uuid

if os.name != "nt":
    import fcntl

INTERVAL = 10800
MAX_STATE = 16384
MAX_TEXT = 2048
EVENTS = {"SessionStart", "UserPromptSubmit", "PostToolUse", "Stop", "Interrupt", "SessionEnd"}
TOKEN = re.compile(r"^[0-9a-f]{32}$")
KEY = re.compile(r"^[0-9a-f]{64}$")
NOTICE = (
    "goal-checkpoint の再評価期限です。まず同梱 goal-checkpoint Skill の review に従い、"
    "最新の goal 状態・予算を確認してください。完了条件の達成証拠を前回と比較し、"
    "停滞の原因と次の具体的な実装を決めてください。終了・停止済みなら監視を解除し、"
    "開発を再開しないでください。再評価結果を記録してから pending を ack してください。"
    "この通知は目的や権限を変更しません。発火ID: "
)


class StateError(Exception):
    pass


def text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value.encode()) > MAX_TEXT:
        raise StateError(f"{label}: 空でない2KiB以内の文字列が必要です")
    return value


def timestamp(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
        raise StateError("時刻が不正です")
    return value


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def bounded_json(raw):
    if len(raw) > MAX_STATE:
        raise StateError("状態JSONが16KiBを超えています")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise StateError("JSON objectが必要です")
    return value


class PosixStore:
    """All mutable files live in a private, non-symlink directory under PLUGIN_DATA."""

    def __init__(self, data):
        if not data:
            raise StateError("PLUGIN_DATA がありません。監視は有効化されていません")
        self.base = Path(data)
        self.fd = None

    def __enter__(self):
        root = os.open(self.base, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            try:
                os.mkdir("goal-checkpoint", mode=0o700, dir_fd=root)
            except FileExistsError:
                pass
            self.fd = os.open("goal-checkpoint", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
            info = os.fstat(self.fd)
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise StateError("状態ディレクトリは所有者専用である必要があります")
        except BaseException:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None
            raise
        finally:
            os.close(root)
        return self

    def __exit__(self, *args):
        os.close(self.fd)

    @contextlib.contextmanager
    def lock(self, session):
        fd = os.open(f"{digest(session)}.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        try:
            self.check_file(fd)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise StateError("別のイベントが状態を更新中です。次のイベントで再確認します") from exc
            yield
        finally:
            os.close(fd)

    @staticmethod
    def check_file(fd):
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise StateError("状態ファイルの種類・所有者・権限が不正です")

    def read(self, name):
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
        except FileNotFoundError:
            return None
        with os.fdopen(fd, "rb") as handle:
            self.check_file(handle.fileno())
            return bounded_json(handle.read(MAX_STATE + 1))

    def write(self, name, value, recover=False):
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        bounded_json(raw)
        # Reject a symlink or an unsafe pre-existing destination before replacement.
        try:
            self.read(name)
        except (json.JSONDecodeError, UnicodeDecodeError, StateError):
            if not recover:
                raise
            # Recovery may replace corrupt JSON, never unsafe filesystem objects.
            info = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise StateError("不正な状態ファイルを置換できません")
        temporary = f".{uuid.uuid4().hex}.tmp"
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, name, src_dir_fd=self.fd, dst_dir_fd=self.fd)
        finally:
            try:
                os.unlink(temporary, dir_fd=self.fd)
            except FileNotFoundError:
                pass

    def load(self, session):
        index = self.read(f"{digest(session)}.index.json")
        if index is None:
            return None
        key = index.get("key")
        generation = index.get("generation")
        if not isinstance(key, str) or not KEY.fullmatch(key) or not isinstance(generation, str) or not TOKEN.fullmatch(generation):
            raise StateError("session index が不正です。enableで再登録してください")
        state = self.read(f"{key}.state.json")
        if state is None or state.get("generation") != generation or state.get("session") != session:
            raise StateError("indexと状態の世代が一致しません。enableで再登録してください")
        workspace = text(state.get("workspace"), "workspace")
        if digest(session + "\0" + workspace) != key or not Path(workspace).is_absolute():
            raise StateError("workspaceの状態キーが不正です")
        validate_state(state)
        return state

    def save(self, state):
        validate_state(state)
        key = digest(state["session"] + "\0" + state["workspace"])
        self.write(f"{key}.state.json", state)

    def enable(self, session, workspace, details, now):
        key = digest(session + "\0" + workspace)
        state = {
            "version": 1, "session": session, "workspace": workspace,
            "generation": uuid.uuid4().hex, "active": True,
            **baseline(details), "baseline_at": now, "due_at": now + INTERVAL,
            "last_clock": now, "pending": None, "ack_at": None,
            "stalled_count": 0, "stop_turn": None, "interrupted_turn": None,
            "disabled_reason": None,
        }
        validate_state(state)
        self.write(f"{key}.state.json", state, recover=True)
        self.write(f"{digest(session)}.index.json", {"key": key, "generation": state["generation"]}, recover=True)
        return state


if os.name == "nt":
    import importlib.util

    _store_spec = importlib.util.spec_from_file_location("checkpoint_windows_store", Path(__file__).with_name("windows_store.py"))
    _store_module = importlib.util.module_from_spec(_store_spec)
    _store_spec.loader.exec_module(_store_module)
    WindowsStore = _store_module.WindowsStore

    class Store(WindowsStore, PosixStore):
        def __init__(self, data):
            WindowsStore.__init__(self, data, error=StateError, bounded_json=bounded_json)
else:
    Store = PosixStore


def baseline(details):
    if details.get("goal_status") != "active" or details.get("budget_exhausted") is not False:
        raise StateError("activeかつ予算未終了のgoal確認が必要です")
    return {key: text(details.get(key), key) for key in ("goal_ref", "milestone", "criteria", "evidence")}


def validate_state(state):
    if state.get("version") != 1 or type(state.get("active")) is not bool:
        raise StateError("状態形式が不正です")
    for field in ("session", "workspace", "goal_ref", "milestone", "criteria", "evidence"):
        text(state.get(field), field)
    if not TOKEN.fullmatch(str(state.get("generation", ""))):
        raise StateError("監視世代が不正です")
    for field in ("baseline_at", "due_at", "last_clock"):
        timestamp(state.get(field))
    count = state.get("stalled_count")
    if type(count) is not int or count < 0:
        raise StateError("停滞回数が不正です")
    for field in ("stop_turn", "interrupted_turn", "disabled_reason"):
        if state.get(field) is not None:
            text(state[field], field)
    if state.get("ack_at") is not None:
        timestamp(state["ack_at"])
    pending = state.get("pending")
    if pending is not None:
        if not isinstance(pending, dict) or not TOKEN.fullmatch(str(pending.get("id", ""))):
            raise StateError("pendingが不正です")
        timestamp(pending.get("notified_at"))
        for field in ("delivery", "start_delivery"):
            if pending.get(field) is not None:
                text(pending[field], field)


def event_update(state, event, now):
    """Return (output, changed). No project/goal text is interpolated into output."""
    name = event["hook_event_name"]
    if not state["active"] or name == "SessionEnd":
        return {}, False
    cwd = Path(text(event.get("cwd"), "cwd")).resolve()
    if not cwd.is_relative_to(Path(state["workspace"])):
        return {}, False
    turn = event.get("turn_id")
    if turn is not None:
        turn = text(turn, "turn_id")
    if name == "Interrupt":
        if turn is None:
            raise StateError("Interruptのturn_idがありません")
        state["interrupted_turn"] = turn
    if now < state["last_clock"]:
        state["due_at"] = now + INTERVAL
        state["last_clock"] = now
        return {"systemMessage": "goal-checkpoint: 時計の後退を検出し、期限を3時間後に再設定しました"}, True
    if name == "Interrupt":
        state["last_clock"] = now
        return {}, True
    changed = False
    if state["pending"] is None:
        if now < state["due_at"]:
            return {}, False
        state["pending"] = {"id": uuid.uuid4().hex, "notified_at": now, "delivery": None}
        changed = True
    pending = state["pending"]
    context = NOTICE + pending["id"]
    if name == "Stop":
        if turn is None:
            raise StateError("Stopのturn_idがありません")
        if event.get("stop_hook_active") or state["stop_turn"] == turn or state["interrupted_turn"] == turn:
            return {}, changed
        state["stop_turn"] = turn
        state["last_clock"] = now
        return {"decision": "block", "reason": context}, True
    # SessionStart has no turn_id. Track resume/compact separately from turn delivery.
    field = "delivery" if turn else "start_delivery"
    delivery = turn if turn else text(event.get("source"), "source")
    if pending.get(field) == delivery:
        return {}, changed
    pending[field] = delivery
    state["last_clock"] = now
    return {"hookSpecificOutput": {"hookEventName": name, "additionalContext": context}}, True


def operate(store, operation, session, workspace, details, now):
    text(session, "session")
    timestamp(now)
    with store.lock(session):
        if operation == "enable":
            workspace = str(Path(text(workspace, "workspace")).resolve(strict=True))
            if not Path(workspace).is_dir():
                raise StateError("workspaceはディレクトリである必要があります")
            return store.enable(session, workspace, details, now)
        state = store.load(session)
        if state is None:
            if operation in {"status", "disable"}:
                return {"active": False, "registered": False}
            raise StateError("監視が未登録です。enableしてください")
        if operation == "status":
            return state
        if operation == "disable":
            state["active"] = False
            state["pending"] = None
            state["disabled_reason"] = text(details.get("reason"), "reason")
        elif operation == "resume":
            if state["active"]:
                raise StateError("既に有効です。status/reviewを使ってください")
            return store.enable(session, state["workspace"], details, now)
        elif operation == "review":
            if not state["active"]:
                raise StateError("監視は無効です")
            if state["pending"] is None:
                state["pending"] = {"id": uuid.uuid4().hex, "notified_at": now, "delivery": None}
        elif operation == "baseline":
            fresh = baseline(details)
            if not state["active"] or details.get("generation") != state["generation"] or fresh["goal_ref"] != state["goal_ref"]:
                raise StateError("Baseline identity does not match active monitoring")
            state.update(fresh)
        elif operation == "ack":
            if not state["active"] or details.get("generation") != state["generation"] or not state["pending"] or details.get("checkpoint_id") != state["pending"]["id"]:
                raise StateError("ackの監視世代・発火IDが現在のpendingと一致しません")
            fresh = baseline(details)
            if fresh["goal_ref"] != state["goal_ref"]:
                raise StateError("goal参照が変わっています。新しいgoalはenableしてください")
            if details.get("verdict") not in {"progress", "stalled"}:
                raise StateError("verdictはprogressまたはstalledです")
            same = fresh["milestone"] == state["milestone"] and fresh["criteria"] == state["criteria"]
            state["stalled_count"] = state["stalled_count"] + 1 if same and details["verdict"] == "stalled" else int(details["verdict"] == "stalled")
            state.update(fresh)
            state.update(baseline_at=now, ack_at=now, due_at=now + INTERVAL, last_clock=now, pending=None)
        else:
            raise StateError("不明な操作です")
        store.save(state)
        return state


def emit(value):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False)
    if len(raw.encode()) > 4096:
        raise StateError("hook出力が4KiBを超えています")
    print(raw)


def run_hook(data, event, now):
    name = event.get("hook_event_name")
    if name not in EVENTS or name == "SessionEnd":
        return {}
    session = text(event.get("session_id"), "session_id")
    with Store(data) as store, store.lock(session):
        state = store.load(session)
        if name == "PostToolUse" and event.get("tool_name") in {"create_goal", "functions.create_goal"}:
            response = event.get("tool_response")
            if isinstance(response, str):
                response = bounded_json(response.encode())
            goal = response.get("goal") if isinstance(response, dict) else None
            if not isinstance(goal, dict) or goal.get("status") != "active":
                return {"systemMessage": "goal-checkpoint: goal の作成結果を確認できません。get_goal と監視状態を確認してください"}
            invocation = event.get("tool_use_id")
            if not isinstance(invocation, str) or not invocation.strip():
                return {"systemMessage": "goal-checkpoint: goal 作成イベントの識別子がありません。監視登録を確認してください"}
            reference = "native-monitor:" + digest(text(invocation, "tool_use_id"))
            if state is not None and state["goal_ref"] == reference:
                return {}
            workspace = str(Path(text(event.get("cwd"), "cwd")).resolve(strict=True))
            if not Path(workspace).is_dir():
                raise StateError("workspace must be a directory")
            store.enable(session, workspace, {
                "goal_status": "active", "budget_exhausted": False,
                "goal_ref": reference, "milestone": "Unconfirmed: inspect the approved plan",
                "criteria": "Unconfirmed: inspect the current native goal and approved criteria",
                "evidence": "Monitoring registered at native goal creation; implementation baseline unconfirmed",
            }, timestamp(now))
            return {"hookSpecificOutput": {"hookEventName": name, "additionalContext":
                "goal-checkpoint: 新しい goal の3時間監視を登録しました。同梱 skill で最新 goal と既存計画の baseline を確認してください。開始時刻を再設定せず、不明な項目を達成済みと扱わないでください。"}}
        if state is None:
            return {}
        output, changed = event_update(state, event, timestamp(now))
        if changed:
            store.save(state)
        return output


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="goal-checkpoint local state")
    parser.add_argument("operation", choices=("hook", "enable", "status", "review", "baseline", "ack", "disable", "resume"))
    parser.add_argument("--session", default=os.environ.get("CODEX_THREAD_ID"))
    parser.add_argument("--workspace", default=os.getcwd())
    args = parser.parse_args()
    hook = args.operation == "hook"
    try:
        data = os.environ.get("PLUGIN_DATA")
        if hook:
            # Ignore tool input/output; only the common event envelope is used.
            raw = sys.stdin.buffer.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise StateError("hook入力が1MiBを超えています")
            event = json.loads(raw)
            if not isinstance(event, dict):
                raise StateError("hook入力がobjectではありません")
            emit(run_hook(data, event, time.time()))
        else:
            details = bounded_json(sys.stdin.buffer.read(MAX_STATE + 1)) if args.operation in {"enable", "resume", "baseline", "ack", "disable"} else {}
            with Store(data) as store:
                result = operate(store, args.operation, args.session, args.workspace, details, time.time())
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except (StateError, OSError, ValueError, TypeError) as exc:
        if hook:
            # Never echo input, file contents or exception text into developer context.
            emit({"systemMessage": "goal-checkpoint: 状態確認に失敗しました。statusで原因を確認し、必要ならenableで再登録してください"})
            return 0
        print(f"goal-checkpoint: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
