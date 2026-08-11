from splunk_app_ci.cli import main


def _app_conf(app_id="apius_lang_entropy"):
    return (
        "[launcher]\nauthor = Apius Technologies\nversion = 1.0.0\n"
        "\n[package]\nid = " + app_id + "\n"
    )


def _make_app_dir(root, app_id="apius_lang_entropy"):
    app = root / app_id
    (app / "default").mkdir(parents=True)
    (app / "default" / "app.conf").write_text(_app_conf(app_id))
    (app / "bin").mkdir()
    (app / "bin" / "entropy_lib.py").write_text("x = 1\n")
    return app


def test_cli_package_builds_tarball(tmp_path, capsys):
    app = _make_app_dir(tmp_path)
    dest = tmp_path / "dist"
    rc = main(
        ["package", "--app-dir", str(app), "--version", "2.3.4", "--dest", str(dest)]
    )
    assert rc == 0
    printed = capsys.readouterr().out.strip()
    assert printed.endswith("apius_lang_entropy-2.3.4.tar.gz")
    assert (dest / "apius_lang_entropy-2.3.4.tar.gz").exists()


def test_cli_stamp_syncs_app_conf_and_pyproject(tmp_path):
    conf = tmp_path / "app.conf"
    conf.write_text(_app_conf())
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "x"\nversion = "0.0.0"\n')

    rc = main(
        [
            "stamp",
            "--version",
            "2.3.4",
            "--app-conf",
            str(conf),
            "--pyproject",
            str(pyproject),
        ]
    )
    assert rc == 0
    assert "version = 2.3.4\n" in conf.read_text()
    assert 'version = "2.3.4"\n' in pyproject.read_text()


def test_cli_current_version_prints_stamped_version(tmp_path, capsys):
    conf = tmp_path / "app.conf"
    conf.write_text(_app_conf())

    rc = main(["current-version", "--app-conf", str(conf)])

    assert rc == 0
    # bare value on stdout: the release workflow captures this in a shell $( )
    assert capsys.readouterr().out == "1.0.0\n"
