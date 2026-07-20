import tarfile

import pytest

from splunk_app_ci.packaging import (
    build_package,
    stamp_conf_version,
    stamp_pyproject_version,
)


def _make_app_dir(root, app_id="apius_lang_entropy"):
    app = root / app_id
    (app / "default").mkdir(parents=True)
    (app / "default" / "app.conf").write_text(
        "[launcher]\nauthor = Apius Technologies\nversion = 1.0.0\n"
        "\n[package]\nid = " + app_id + "\n"
    )
    (app / "bin").mkdir()
    (app / "bin" / "entropy_lib.py").write_text("x = 1\n")
    (app / "bin" / "lib" / "splunklib").mkdir(parents=True)
    (app / "bin" / "lib" / "splunklib" / "__init__.py").write_text("# vendored\n")
    # junk that must NOT ship
    (app / "bin" / "__pycache__").mkdir()
    (app / "bin" / "__pycache__" / "entropy_lib.cpython-39.pyc").write_bytes(b"\x00")
    (app / ".DS_Store").write_bytes(b"\x00")
    return app


def test_stamp_conf_version_sets_launcher_version():
    conf = (
        "[launcher]\n"
        "author = Apius Technologies\n"
        "description = Scoring app\n"
        "version = 1.0.0\n"
        "\n"
        "[package]\n"
        "id = apius_lang_entropy\n"
    )
    out = stamp_conf_version(conf, "2.3.4")
    assert "version = 2.3.4\n" in out
    # untouched: everything else stays byte-for-byte
    assert "version = 1.0.0" not in out
    assert "author = Apius Technologies\n" in out
    assert "id = apius_lang_entropy\n" in out


def test_stamp_conf_version_raises_when_stanza_key_absent():
    with pytest.raises(ValueError, match="launcher"):
        stamp_conf_version("[package]\nid = x\n", "1.2.3")


def test_stamp_pyproject_version_sets_project_version_only():
    pyproject = (
        "[project]\n"
        'name = "apius_lang_entropy"\n'
        'version = "0.0.0"\n'
        "\n"
        "[tool.ruff]\n"
        'target-version = "py39"\n'
    )
    out = stamp_pyproject_version(pyproject, "2.3.4")
    assert 'version = "2.3.4"\n' in out
    assert 'version = "0.0.0"' not in out
    # the ruff table's own version-like key must be untouched
    assert 'target-version = "py39"\n' in out


def test_build_package_produces_stamped_splunkbase_tarball(tmp_path):
    app = _make_app_dir(tmp_path)
    dest = tmp_path / "dist"

    pkg = build_package(app, "2.3.4", dest)

    assert pkg.exists() and pkg.suffix == ".gz"
    with tarfile.open(pkg) as tar:
        names = tar.getnames()
        # single top-level entry == app id
        tops = {n.split("/")[0] for n in names}
        assert tops == {"apius_lang_entropy"}
        # vendored lib retained
        assert "apius_lang_entropy/bin/lib/splunklib/__init__.py" in names
        # junk excluded
        assert not any("__pycache__" in n or n.endswith(".pyc") for n in names)
        assert not any(n.endswith(".DS_Store") for n in names)
        # app.conf inside the package carries the stamped version
        member = tar.extractfile("apius_lang_entropy/default/app.conf")
        assert "version = 2.3.4\n" in member.read().decode()


def test_build_package_rejects_dir_without_app_conf(tmp_path):
    not_an_app = tmp_path / "whatever"
    (not_an_app / "bin").mkdir(parents=True)
    with pytest.raises(ValueError, match="app.conf"):
        build_package(not_an_app, "1.0.0", tmp_path / "dist")
