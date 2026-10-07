"""Claude/Codex adapter over the same checkpoint engine; no fabricated native goals."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid

import checkpoint as core


def claude_hook(data, event, now):
    name = event.get('hook_event_name')
    if name not in {'SessionStart', 'UserPromptSubmit', 'PostToolUse', 'Stop', 'SessionEnd'} or name == 'SessionEnd':
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
            output = claude_hook(str(data), event, time.time()) if args.host == 'claude' else core.run_hook(str(data), event, time.time())
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
