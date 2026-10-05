import argparse
import os
from pathlib import Path
import sys

from .catalog import Catalog
from .codec import Failure, canonical, fields, identifier, result, version
from .storage import read_json
from .transport import send


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Failure()


def parser():
    value = Parser(prog="accountctl")
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    value.add_argument("--catalog", default=str(home / "site-catalog"))
    value.add_argument("--client", default=str(home / "account-catalog-client.json"))
    sub = value.add_subparsers(dest="command", required=True)
    find = sub.add_parser("find")
    find.add_argument("query")
    identity = sub.add_parser("identity")
    identity.add_argument("identity_id")
    identity.add_argument("field")
    identity.add_argument("--site")
    notation = sub.add_parser("license")
    notation.add_argument("notation_id")
    describe = sub.add_parser("describe")
    describe.add_argument("target_id")
    for name in ("login", "run"):
        operation = sub.add_parser(name)
        operation.add_argument("target_id")
        if name == "run":
            operation.add_argument("action_id")
    return value


def main(argv=None):
    target = "invalid"
    try:
        args = parser().parse_args(argv)
        catalog = Catalog(args.catalog)
        if args.command == "find":
            output = catalog.find(args.query)
        elif args.command == "identity":
            output = catalog.identity(args.identity_id, args.field, args.site)
        elif args.command == "license":
            output = catalog.notation(args.notation_id)
        elif args.command == "describe":
            output = catalog.read("targets", args.target_id)
        else:
            target = identifier(args.target_id)
            action = "sign_in" if args.command == "login" else identifier(args.action_id)
            if action not in {"sign_in", "health-check"}:
                raise Failure("not_authorized")
            config = read_json(args.client)
            fields(config, ("schema_version", "endpoint", "broker_id"))
            version(config)
            if any(not isinstance(config[k], str) or not config[k] for k in ("endpoint", "broker_id")):
                raise Failure()
            output = send(config["endpoint"], config["broker_id"], {"schema_version": 1,
                          "target_id": target, "action_id": action})
        sys.stdout.buffer.write(canonical(output) + b"\n")
        return 0 if output.get("status") not in {"failed", "needs_user"} else 2
    except Failure as exc:
        sys.stdout.buffer.write(canonical(result(target, "failed", exc.code)) + b"\n")
        return 2
    except (OSError, ValueError, TypeError):
        sys.stdout.buffer.write(canonical(result(target, "failed", "unavailable")) + b"\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
