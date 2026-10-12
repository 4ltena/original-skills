"""Claude/Codex adapter over the same checkpoint engine; no fabricated native goals."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import threading
import uuid

import checkpoint as core


OBSERVATIONS = 'hook-observations.json'
OBSERVATION_RETRIES = 16
OBSERVATION_THREAD_LOCK = threading.Lock()
CLAUDE_EVENTS = {'SessionStart', 'UserPromptSubmit', 'PostToolUse', 'Stop', 'SessionEnd'}


def record_observation(data, event, now, elapsed_ms, outcome, supported_events=core.EVENTS):
    """Best-effort, content-free hook receipt. It must never affect hook behavior."""
    name = event.get('hook_event_name')
    if name not in supported_events:
        return
    elapsed = max(0, int(elapsed_ms))
    # Store locks deliberately fail fast. A tiny bounded retry keeps concurrent
    # sessions from dropping ordinary receipts without delaying a hook materially.
    with OBSERVATION_THREAD_LOCK:
        for attempt in range(OBSERVATION_RETRIES):
            try:
                with core.Store(data) as store, store.lock('hook-observations'):
                    receipt = store.read(OBSERVATIONS)
                    if receipt is None:
                        receipt = {'version': 1, 'observations': []}
                    observations = receipt.get('observations') if isinstance(receipt, dict) and receipt.get('version') == 1 else None
                    if not isinstance(observations, list):
                        raise core.StateError('invalid observation receipt')
                    normalized = []
                    for item in observations:
                        if (not isinstance(item, dict) or item.get('event') not in supported_events
                                or item.get('outcome') not in {'ok', 'error'}):
                            raise core.StateError('invalid observation receipt')
                        core.timestamp(item.get('at'))
                        if type(item.get('elapsed_ms')) is not int or item['elapsed_ms'] < 0:
                            raise core.StateError('invalid observation receipt')
                        normalized.append({key: item[key] for key in ('event', 'at', 'elapsed_ms', 'outcome')})
                    normalized.append({'event': name, 'at': core.timestamp(now), 'elapsed_ms': elapsed, 'outcome': outcome})
                    receipt = {'version': 1, 'observations': normalized[-32:]}
                    store.write(OBSERVATIONS, receipt)
                    return
            except core.StateError:
                if attempt + 1 < OBSERVATION_RETRIES:
                    time.sleep(0.001)
            except (OSError, OverflowError, ValueError, TypeError):
                return


def observed_hook(data, event, now, handler, supported_events=core.EVENTS):
    started = time.perf_counter()
    try:
        output = handler(data, event, now)
    except BaseException:
        record_observation(data, event, now, (time.perf_counter() - started) * 1000, 'error', supported_events)
        raise
    record_observation(data, event, now, (time.perf_counter() - started) * 1000, 'ok', supported_events)
    return output


def _claude_hook(data, event, now):
    name = event.get('hook_event_name')
    if name not in CLAUDE_EVENTS or name == 'SessionEnd':
        return {}
    session = 'claude:' + core.text(event.get('session_id'), 'session_id')
    # Claude has no turn_id. Record a fresh adapter turn at each UserPromptSubmit,
    # not a hash of prompt text, which would retain or conflate user input.
    with core.Store(data) as store, store.lock(session):
        turn_key = core.digest('claude-turn:' + session) + '.index.json'
        turn = store.read(turn_key)
        if name == 'UserPromptSubmit':
            turn = {'id': uuid.uuid4().hex}
            store.write(turn_key, turn)
        state = store.load(session)
        if state is None:
            return {}
        normalized = {'hook_event_name': name, 'session_id': session,
            'cwd': event.get('cwd'), 'source': event.get('source') or 'startup',
            'stop_hook_active': event.get('stop_hook_active') is True}
        if turn is not None and name != 'SessionStart':
            if not isinstance(turn, dict) or not core.TOKEN.fullmatch(str(turn.get('id', ''))):
                raise core.StateError('invalid Claude turn')
            normalized['turn_id'] = turn['id']
        elif name == 'Stop':
            return {'systemMessage': 'goal-checkpoint: session turn is unknown; review manually before acknowledging'}
        output, changed = core.event_update(state, normalized, core.timestamp(now))
        if changed:
            store.save(state)
        # A Claude monitor tracks the explicit objective, not Codex native goal APIs.
        def translate(value):
            if isinstance(value, str):
                return value.replace('最新の goal 状態・予算', '明示した目的・計画の状態と停止指示')
            if isinstance(value, dict):
                return {key: translate(item) for key, item in value.items()}
            return value
        return translate(output)


def claude_hook(data, event, now):
    return observed_hook(data, event, now, _claude_hook, CLAUDE_EVENTS)


def operate(data, host, operation, session, workspace, details, now):
    if host == 'claude':
        session = 'claude:' + core.text(session, 'session_id')
    with core.Store(data) as store:
        return core.operate(store, operation, session, workspace, details, now)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('hook', 'enable', 'status', 'review', 'baseline', 'ack', 'disable', 'resume'))
    parser.add_argument('--host', choices=('claude', 'codex'), required=True)
    parser.add_argument('--session')
    parser.add_argument('--workspace', default=os.getcwd())
    parser.add_argument('--binding', default=str(Path(__file__).resolve().parents[1] / 'binding.json'))
    args = parser.parse_args()
    try:
        binding = json.loads(Path(args.binding).read_text(encoding='utf-8'))
        if (binding.get('runtime') != args.host or sys.version_info < (3, 10)
                or Path(binding['executable']).resolve() != Path(sys.executable).resolve()):
            raise core.StateError('use the verified host Python binding')
        data = Path(binding['data'])
        if not data.is_absolute():
            raise core.StateError('absolute data path required')
        # State files themselves are owner-only and handle/FD-validated by core.Store.
        for path in [*reversed(data.parents), data]:
            if path.is_symlink() or path.exists() and getattr(path.lstat(), 'st_file_attributes', 0) & 0x400:
                raise core.StateError('unsafe data path')
        data.mkdir(mode=0o700, parents=True, exist_ok=True)
        if args.operation == 'hook':
            raw = sys.stdin.buffer.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise core.StateError('hook input too large')
            event = json.loads(raw)
            if not isinstance(event, dict):
                raise core.StateError('hook object required')
            now = time.time()
            output = claude_hook(str(data), event, now) if args.host == 'claude' else observed_hook(str(data), event, now, core.run_hook)
            core.emit(output)
        else:
            details = core.bounded_json(sys.stdin.buffer.read(core.MAX_STATE + 1)) if args.operation in {'enable', 'resume', 'baseline', 'ack', 'disable'} else {}
            session = args.session or (os.environ.get('CODEX_THREAD_ID') if args.host == 'codex' else None)
            print(json.dumps(operate(str(data), args.host, args.operation, session, args.workspace, details, time.time()), ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError, core.StateError):
        if args.operation == 'hook':
            core.emit({'systemMessage': 'goal-checkpoint: host state unavailable; inspect status before resuming'})
            return 0
        print('goal-checkpoint: operation refused; check binding, session and baseline', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
