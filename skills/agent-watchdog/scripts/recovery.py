"""CLI-independent recovery decision from explicit run evidence. Does not spawn/retry."""
import json
import sys


def decide(evidence):
    if not isinstance(evidence, dict):
        raise ValueError('evidence object required')
    attempts = evidence.get('attempts')
    if type(attempts) is not int or attempts < 1:
        raise ValueError('positive attempt count required')
    kind = evidence.get('failure_kind')
    if kind not in {'unknown', 'transient', 'deterministic', 'user-stop'}:
        raise ValueError('classified failure required')
    for field in ('repeatable', 'user_stopped', 'uncertain_effects'):
        if type(evidence.get(field)) is not bool:
            raise ValueError('explicit safety evidence required')
    if evidence['user_stopped'] or kind in {'user-stop', 'deterministic'}:
        action, reason = 'stop', 'stop instruction or deterministic failure'
    elif not evidence['repeatable'] or evidence['uncertain_effects']:
        action, reason = 'stop', 'safe repeatability is unconfirmed'
    elif attempts >= 3 or attempts >= 2 and kind != 'transient':
        action, reason = 'stop', 'bounded retry cap reached'
    else:
        action, reason = 'resume-missing-work', 'one recovery owner must inspect artifacts and update attempt evidence'
    return {'action': action, 'attempts': attempts, 'next_attempt': attempts + 1 if action != 'stop' else None, 'reason': reason}


def main():
    try:
        raw = sys.stdin.buffer.read(16385)
        if len(raw) > 16384:
            raise ValueError('evidence too large')
        print(json.dumps(decide(json.loads(raw))))
    except (ValueError, TypeError, KeyError):
        print('recovery: insufficient evidence; no retry', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
