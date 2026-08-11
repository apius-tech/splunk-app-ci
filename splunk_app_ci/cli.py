"""Command-line entry point for the splunk-app-ci packaging tooling.

Used by the reusable release workflow:

    # build the Splunkbase artifact (stamps app.conf inside the package)
    python -m splunk_app_ci package --app-dir <app_id> --version X.Y.Z --dest dist

    # stamp the source files in place (app.conf + pyproject.toml) so the repo
    # version stays in sync with the release tag
    python -m splunk_app_ci stamp --version X.Y.Z \
        --app-conf <app_id>/default/app.conf --pyproject pyproject.toml

    # read back the stamped version, so the release flow derives it from the
    # repo instead of a human retyping it into a tag
    python -m splunk_app_ci current-version --app-conf <app_id>/default/app.conf
"""

import argparse
from pathlib import Path

from splunk_app_ci.packaging import (
    build_package,
    read_conf_version,
    stamp_conf_version,
    stamp_pyproject_version,
)


def _cmd_package(args):
    pkg = build_package(args.app_dir, args.version, args.dest)
    print(pkg)
    return 0


def _cmd_stamp(args):
    conf = Path(args.app_conf)
    conf.write_text(stamp_conf_version(conf.read_text(), args.version))
    if args.pyproject:
        pp = Path(args.pyproject)
        pp.write_text(stamp_pyproject_version(pp.read_text(), args.version))
    return 0


def _cmd_current_version(args):
    print(read_conf_version(Path(args.app_conf).read_text()))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="splunk_app_ci")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("package", help="build a Splunkbase .tar.gz")
    p.add_argument("--app-dir", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--dest", required=True)
    p.set_defaults(func=_cmd_package)

    s = sub.add_parser("stamp", help="stamp version into source files in place")
    s.add_argument("--version", required=True)
    s.add_argument("--app-conf", required=True)
    s.add_argument("--pyproject", default=None)
    s.set_defaults(func=_cmd_stamp)

    v = sub.add_parser(
        "current-version", help="print the version currently stamped in app.conf"
    )
    v.add_argument("--app-conf", required=True)
    v.set_defaults(func=_cmd_current_version)

    args = parser.parse_args(argv)
    return args.func(args)
