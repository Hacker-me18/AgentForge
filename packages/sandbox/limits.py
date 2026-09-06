"""Resource limits applied to sandboxed code execution containers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceLimits:
    """Resource limits for a single sandbox run.

    Attributes:
        network: Docker network mode. Defaults to ``none`` (fully isolated).
        timeout_s: Wall-clock timeout in seconds for the whole run.
        memory: Docker memory limit (e.g. ``"512m"``, ``"128m"``).
        cpu: Number of CPUs the container may use (fractional allowed).
        tmpfs: Path inside the container backed by an ephemeral tmpfs
            (``/work`` by default); set to ``None`` to disable.
    """

    network: str = "none"
    timeout_s: float = 30.0
    memory: str = "512m"
    cpu: float = 1.0
    tmpfs: str | None = "/work"

    @property
    def nano_cpus(self) -> int:
        """CPU limit expressed as nano CPUs (1 cpu = 1e9 nano cpus)."""
        return int(self.cpu * 1_000_000_000)
