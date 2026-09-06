"""Tests for Phase D: Docker sandbox execution.

These tests require a running Docker daemon and the ``agentos-sandbox:0.1``
image (see ``docker/sandbox.Dockerfile``). When Docker is unavailable the
whole module is skipped so CI / Docker-less environments stay green.
"""

import shutil
import subprocess

import pytest

from packages.sandbox import (
    DEFAULT_IMAGE,
    DockerExecutor,
    DockerUnavailableError,
    ResourceLimits,
    SandboxRunner,
)


def _docker_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        check = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            timeout=15,
        )
        if check.returncode != 0:
            return False
        image = subprocess.run(
            ["docker", "image", "inspect", DEFAULT_IMAGE],
            capture_output=True,
            timeout=15,
        )
        return image.returncode == 0
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _docker_ready(), reason="docker daemon or agentos-sandbox image unavailable"
)


# ---------------------------------------------------------------------------
# a) normal execution: print + pandas computation
# ---------------------------------------------------------------------------


async def test_sandbox_success_with_pandas(tmp_path) -> None:
    runner = SandboxRunner()
    code = (
        "import pandas as pd\n"
        "print('sum:', int(pd.Series([1, 2, 3]).sum()))\n"
        "print('hello sandbox')\n"
    )
    result = await runner.run(code, artifacts_dir=str(tmp_path))
    assert result.status == "success"
    assert result.exit_code == 0
    assert "hello sandbox" in result.stdout
    assert "sum: 6" in result.stdout
    assert result.duration_ms > 0


# ---------------------------------------------------------------------------
# b) artifacts: matplotlib writes distribution.png under /work
# ---------------------------------------------------------------------------


async def test_sandbox_collects_matplotlib_artifact(tmp_path) -> None:
    runner = SandboxRunner()
    code = (
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        "plt.hist([1, 1, 2, 3, 5, 8])\n"
        "plt.savefig('/work/distribution.png')\n"
        "print('plot saved')\n"
    )
    result = await runner.run(code, artifacts_dir=str(tmp_path))
    assert result.status == "success"
    assert "distribution.png" in result.artifacts
    artifact_file = tmp_path / "distribution.png"
    assert artifact_file.is_file()
    assert artifact_file.stat().st_size > 0


# ---------------------------------------------------------------------------
# c) timeout: sleeping code is killed and reported
# ---------------------------------------------------------------------------


async def test_sandbox_timeout(tmp_path) -> None:
    runner = SandboxRunner()
    limits = ResourceLimits(timeout_s=3)
    result = await runner.run(
        "import time; time.sleep(60)", limits=limits, artifacts_dir=str(tmp_path)
    )
    assert result.status == "timeout"


# ---------------------------------------------------------------------------
# d) network is disabled inside the sandbox
# ---------------------------------------------------------------------------


async def test_sandbox_network_disabled(tmp_path) -> None:
    runner = SandboxRunner()
    code = (
        "import socket\nsocket.create_connection(('8.8.8.8', 53), timeout=5)\nprint('connected')\n"
    )
    result = await runner.run(code, artifacts_dir=str(tmp_path))
    assert result.status != "success"
    assert "connected" not in result.stdout


# ---------------------------------------------------------------------------
# e) memory limit exceeded -> oom (or error) and non-zero exit
# ---------------------------------------------------------------------------


async def test_sandbox_memory_limit(tmp_path) -> None:
    runner = SandboxRunner()
    limits = ResourceLimits(memory="128m", timeout_s=60)
    code = "data = bytearray(2 * 1024**3)\nprint(len(data))\n"
    result = await runner.run(code, limits=limits, artifacts_dir=str(tmp_path))
    assert result.status in ("oom", "error")
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# f) invalid code -> error with non-empty stderr
# ---------------------------------------------------------------------------


async def test_sandbox_syntax_error(tmp_path) -> None:
    runner = SandboxRunner()
    result = await runner.run("def broken(:\n    pass\n", artifacts_dir=str(tmp_path))
    assert result.status == "error"
    assert result.stderr.strip()


# ---------------------------------------------------------------------------
# runner emits sandbox.* events
# ---------------------------------------------------------------------------


async def test_sandbox_runner_emits_events(tmp_path) -> None:
    events: list[tuple[str, dict]] = []
    runner = SandboxRunner(event_recorder=lambda e, p: events.append((e, p)))
    result = await runner.run("print('hi')", artifacts_dir=str(tmp_path))
    assert result.status == "success"
    names = [name for name, _ in events]
    assert names == ["sandbox.started", "sandbox.completed"]
    completed = events[1][1]
    assert completed["image"] == DEFAULT_IMAGE
    assert completed["exit_code"] == 0
    assert completed["duration_ms"] > 0


# ---------------------------------------------------------------------------
# executor raises DockerUnavailableError when the daemon is unreachable
# ---------------------------------------------------------------------------


async def test_executor_reports_unavailable_daemon() -> None:
    executor = DockerExecutor()
    if shutil.which("docker") is None:
        with pytest.raises(DockerUnavailableError):
            await executor.ensure_available()
    else:
        # Daemon is reachable in this environment; nothing to assert beyond
        # the call succeeding.
        await executor.ensure_available()
