"""Docker-based sandbox executor for untrusted Python code.

Uses the ``docker`` CLI via asyncio subprocesses (no Docker SDK dependency).
Code is streamed into the container through stdin, executed with
``python /work/main.py`` and artifacts produced under ``/work`` are copied
back to the host with ``docker cp``. The container is created with
``--network none``, memory/CPU limits and an ephemeral tmpfs on ``/work``;
it is always removed after the run.
"""

import asyncio
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from packages.sandbox.collector import ArtifactCollector
from packages.sandbox.limits import ResourceLimits

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IMAGE = "agentos-sandbox:0.1"
DEFAULT_ARTIFACTS_ROOT = REPO_ROOT / "data" / "artifacts"

STATUS_SUCCESS = "success"
STATUS_TIMEOUT = "timeout"
STATUS_OOM = "oom"
STATUS_ERROR = "error"


class DockerUnavailableError(RuntimeError):
    """Raised when the docker CLI or daemon is not available."""


@dataclass
class SandboxResult:
    status: str = STATUS_ERROR
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    artifacts: list[str] = field(default_factory=list)


async def _run_cli(*args: str, timeout: float = 15) -> tuple[int, str, str]:
    """Run a docker CLI command, returning (returncode, stdout, stderr)."""
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except TimeoutError:
        process.kill()
        await process.wait()
        return -1, "", f"command timed out: {' '.join(args)}"
    return (
        process.returncode or 0,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


class DockerExecutor:
    """Executes Python code inside a locked-down Docker container."""

    def __init__(
        self,
        image: str = DEFAULT_IMAGE,
        artifacts_root: str | Path = DEFAULT_ARTIFACTS_ROOT,
        collector: ArtifactCollector | None = None,
    ):
        self.image = image
        self.collector = collector or ArtifactCollector(artifacts_root)

    async def ensure_available(self) -> None:
        """Raise DockerUnavailableError if the CLI or daemon is unusable."""
        if shutil.which("docker") is None:
            raise DockerUnavailableError("docker CLI not found in PATH")
        rc, _, stderr = await _run_cli(
            "docker", "version", "--format", "{{.Server.Version}}", timeout=10
        )
        if rc != 0:
            detail = stderr.strip() or "docker daemon not responding"
            raise DockerUnavailableError(detail)

    async def execute(
        self,
        code: str,
        *,
        limits: ResourceLimits | None = None,
        artifacts_dir: str | None = None,
    ) -> SandboxResult:
        await self.ensure_available()
        limits = limits or ResourceLimits()
        run_id = uuid.uuid4().hex[:12]
        dest = Path(artifacts_dir) if artifacts_dir else self.collector.destination(run_id)
        dest.mkdir(parents=True, exist_ok=True)
        # Fresh per-run staging dir bind-mounted at /work (ephemeral filesystem:
        # empty at start, deleted after the run). A bind mount is used instead
        # of tmpfs because tmpfs contents vanish when the container exits,
        # which would make artifact collection impossible.
        staging = dest / "_staging"
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "main.py").write_text(code, encoding="utf-8")
        name = f"agentos-sandbox-{run_id}"

        args = [
            "docker",
            "run",
            "--name",
            name,
            "-i",
            "--network",
            limits.network,
            "--memory",
            limits.memory,
            "--cpus",
            str(limits.cpu),
            "-v",
            f"{staging}:/work",
            "--stop-timeout",
            "1",
            self.image,
            "python",
            "/work/main.py",
        ]

        result = SandboxResult(exit_code=None)
        started = time.perf_counter()
        timed_out = False
        process = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=limits.timeout_s,
            )
            result.exit_code = process.returncode
        except TimeoutError:
            timed_out = True
            # Kill the container (the CLI client exits once it dies).
            await _run_cli("docker", "kill", name, timeout=10)
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
            except TimeoutError:
                process.kill()
                stdout, stderr = await process.communicate()
            result.exit_code = process.returncode
        result.duration_ms = (time.perf_counter() - started) * 1000
        result.stdout = stdout.decode("utf-8", errors="replace")
        result.stderr = stderr.decode("utf-8", errors="replace")

        if timed_out:
            result.status = STATUS_TIMEOUT
        elif result.exit_code == 0:
            result.status = STATUS_SUCCESS
        elif await self._oom_killed(name) or result.exit_code == 137:
            result.status = STATUS_OOM
        else:
            result.status = STATUS_ERROR

        # Artifacts are already on the host in the staging dir.
        result.artifacts = self.collector.collect(staging, dest)
        shutil.rmtree(staging, ignore_errors=True)

        # Always remove the container.
        await _run_cli("docker", "rm", "-f", name, timeout=15)
        return result

    async def _oom_killed(self, name: str) -> bool:
        rc, stdout, _ = await _run_cli(
            "docker", "inspect", "--format", "{{.State.OOMKilled}}", name
        )
        return rc == 0 and stdout.strip().lower() == "true"
