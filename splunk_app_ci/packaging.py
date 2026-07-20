"""Version stamping and Splunkbase packaging for Apius Splunk apps."""

import re
import shutil
import tarfile
import tempfile
from pathlib import Path

# Tooling/VCS artifacts that must never ship inside a Splunkbase package.
_PACKAGE_EXCLUDES = ("__pycache__", "*.pyc", "*.pyo", ".DS_Store", ".git")

_STANZA_RE = re.compile(r"^\s*\[(?P<name>[^\]]+)\]\s*$")
_KEY_RE = re.compile(r"^(?P<indent>\s*)version(?P<sep>\s*=\s*)")
_TOML_TABLE_RE = re.compile(r"^\s*\[(?P<name>[^\]]+)\]\s*$")
_TOML_VERSION_RE = re.compile(r'^\s*version\s*=\s*".*"\s*$')


def stamp_conf_version(conf_text, version, stanza="launcher"):
    """Return app.conf text with ``version`` set inside ``[stanza]``.

    Only the target stanza's ``version`` line is rewritten; everything else
    (other stanzas, keys, comments, blank lines) is preserved verbatim.
    """
    lines = conf_text.splitlines(keepends=True)
    out = []
    in_stanza = False
    stamped = False
    for line in lines:
        match = _STANZA_RE.match(line)
        if match:
            in_stanza = match.group("name").strip() == stanza
        elif in_stanza and _KEY_RE.match(line):
            newline = "\n" if line.endswith("\n") else ""
            line = f"version = {version}{newline}"
            stamped = True
        out.append(line)
    if not stamped:
        raise ValueError(f"No [{stanza}] version key found to stamp")
    return "".join(out)


def stamp_pyproject_version(pyproject_text, version):
    """Return pyproject.toml text with ``[project].version`` set to ``version``.

    Only the ``version`` key inside the ``[project]`` table is rewritten; keys
    in other tables (e.g. ``[tool.ruff] target-version``) are left untouched.
    """
    lines = pyproject_text.splitlines(keepends=True)
    out = []
    in_project = False
    stamped = False
    for line in lines:
        table = _TOML_TABLE_RE.match(line)
        if table:
            in_project = table.group("name").strip() == "project"
        elif in_project and _TOML_VERSION_RE.match(line):
            newline = "\n" if line.endswith("\n") else ""
            line = f'version = "{version}"{newline}'
            stamped = True
        out.append(line)
    if not stamped:
        raise ValueError("No [project] version key found to stamp")
    return "".join(out)


def _strip_ownership(tarinfo):
    """Normalize ownership so packages are reproducible across build hosts."""
    tarinfo.uid = tarinfo.gid = 0
    tarinfo.uname = tarinfo.gname = ""
    return tarinfo


def build_package(app_dir, version, dest_dir):
    """Package a Splunk app directory into a Splunkbase-ready ``.tar.gz``.

    ``app_dir`` is the directory whose name is the App id (it contains
    ``default/app.conf``). Returns the path to the created archive, whose sole
    top-level directory is the App id, with ``app.conf`` version stamped to
    ``version`` and tooling/VCS artifacts excluded.

    Raises ValueError if ``app_dir`` is not a Splunk app directory.
    """
    app_dir = Path(app_dir)
    if not (app_dir / "default" / "app.conf").is_file():
        raise ValueError(
            f"Not a Splunk app directory (missing default/app.conf): {app_dir}"
        )
    app_id = app_dir.name
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    ignore = shutil.ignore_patterns(*_PACKAGE_EXCLUDES)
    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp) / app_id
        shutil.copytree(app_dir, staged, ignore=ignore)
        conf = staged / "default" / "app.conf"
        conf.write_text(stamp_conf_version(conf.read_text(), version))

        pkg = dest_dir / f"{app_id}-{version}.tar.gz"
        with tarfile.open(pkg, "w:gz") as tar:
            for path in sorted(staged.rglob("*")):
                tar.add(
                    path,
                    arcname=f"{app_id}/{path.relative_to(staged)}",
                    recursive=False,
                    filter=_strip_ownership,
                )
    return pkg
