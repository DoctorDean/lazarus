"""Sandbox tests using a fake runner -- no Docker daemon required."""

from lazarus.sandbox import CommandResult, DockerClient, Sandbox


class FakeRunner:
    """Records every argv and returns scripted (exit, stdout, stderr) results."""

    def __init__(self, script=None):
        self.calls = []          # list of argv lists
        self.envs = []           # env dict passed with each call
        self._script = list(script or [])

    def __call__(self, argv, *, input_bytes=None, timeout=None, env=None):
        self.calls.append(list(argv))
        self.envs.append(env)
        if self._script:
            return self._script.pop(0)
        return (0, "", "")

    @property
    def last(self):
        return self.calls[-1]


def make_box(script=None, **kwargs):
    runner = FakeRunner(script)
    client = DockerClient(runner=runner)
    box = Sandbox(client, "pablogainza/masif:latest", name="testbox", **kwargs)
    return runner, box


def test_command_result_helpers():
    r = CommandResult("x", 1, "out-line", "err-line", 0.1)
    assert not r.ok
    assert r.combined == "out-line\nerr-line"
    assert r.tail(1) == "err-line"


def test_start_issues_run_with_platform_and_keepalive():
    runner, box = make_box()
    box.start()
    assert box.started
    argv = runner.last
    assert argv[:2] == ["docker", "run"]
    assert "-d" in argv
    assert argv[argv.index("--platform") + 1] == "linux/amd64"
    assert argv[argv.index("--name") + 1] == "testbox"
    assert argv[argv.index("-w") + 1] == "/work"
    assert argv[-3:] == ["pablogainza/masif:latest", "sleep", "infinity"]


def test_start_is_idempotent():
    runner, box = make_box()
    box.start()
    box.start()
    assert sum(1 for c in runner.calls if c[1] == "run") == 1


def test_start_with_gpus_adds_flag():
    runner, box = make_box(gpus="all")
    box.start()
    argv = runner.last
    assert argv[argv.index("--gpus") + 1] == "all"
    assert argv[-2:] == ["sleep", "infinity"]


def test_start_without_gpus_omits_flag():
    runner, box = make_box()
    box.start()
    assert "--gpus" not in runner.last


def test_exec_string_runs_under_bash_lc():
    runner, box = make_box()
    box.start()
    box.exec("echo hi", workdir="/masif", env={"MASIF": "1"})
    argv = runner.last
    assert argv[1] == "exec"
    assert argv[argv.index("-w") + 1] == "/masif"
    assert "-e" in argv and "MASIF=1" in argv
    assert argv[-3:] == ["bash", "-lc", "echo hi"]


def test_exec_list_runs_directly():
    runner, box = make_box()
    box.start()
    box.exec(["python", "predict.py"])
    assert runner.last[-2:] == ["python", "predict.py"]


def test_put_and_get_use_docker_cp():
    runner, box = make_box()
    box.start()
    box.put("/local/in.pdb", "/work/in.pdb")
    assert runner.last == ["docker", "cp", "/local/in.pdb", "testbox:/work/in.pdb"]
    box.get("/work/out.npy", "/local/out.npy")
    assert runner.last == ["docker", "cp", "testbox:/work/out.npy", "/local/out.npy"]


def test_snapshot_commits_and_returns_tag():
    runner, box = make_box()
    box.start()
    tag = box.snapshot("lazarus/masif:site-ready", message="binary chain resolved")
    assert tag == "lazarus/masif:site-ready"
    argv = runner.last
    assert argv[:2] == ["docker", "commit"]
    assert argv[argv.index("-m") + 1] == "binary chain resolved"
    assert argv[-2:] == ["testbox", "lazarus/masif:site-ready"]


def test_context_manager_starts_and_removes():
    runner = FakeRunner()
    client = DockerClient(runner=runner)
    with Sandbox(client, "img", name="cm") as box:
        assert box.started
    assert runner.last == ["docker", "rm", "-f", "cm"]


def test_failed_lifecycle_command_raises():
    import pytest
    from lazarus.sandbox import DockerError

    runner, box = make_box(script=[(1, "", "no such image")])
    with pytest.raises(DockerError):
        box.start()


def test_remote_host_sets_docker_host_env():
    runner = FakeRunner()
    client = DockerClient(runner=runner, docker_host="ssh://you@gpu-box")
    client.run(["ps"])
    assert runner.envs[-1] == {"DOCKER_HOST": "ssh://you@gpu-box"}


def test_local_host_passes_no_docker_host_env():
    runner = FakeRunner()
    client = DockerClient(runner=runner)
    client.run(["ps"])
    assert runner.envs[-1] is None
