"""Multi-destination transfer orchestration for ROMPy."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .registry import get_transfer
from .utils import join_prefix


class TransferFailurePolicy(Enum):
    """Policy for handling transfer failures when uploading to multiple destinations.

    Attributes:
        CONTINUE: Record failures but continue with remaining transfers
        FAIL_FAST: Stop and raise exception on first failure
    """

    CONTINUE = "continue"
    FAIL_FAST = "fail_fast"


@dataclass
class TransferItemResult:
    """Result of transferring a single file to a single destination.

    Attributes:
        local_path: Source file path on local filesystem
        dest_prefix: Destination prefix (treated as folder-like)
        target_name: Target filename to append to prefix
        dest_uri: Final constructed URI (prefix + target_name)
        ok: True if transfer succeeded, False otherwise
        error: Error message if transfer failed, None if succeeded
    """

    local_path: Path
    dest_prefix: str
    target_name: str
    dest_uri: str
    ok: bool
    error: Optional[str] = None


@dataclass
class TransferBatchResult:
    """Aggregated results from transferring files to multiple destinations.

    Attributes:
        total: Total number of transfer attempts
        succeeded: Number of successful transfers
        failed: Number of failed transfers
        items: Detailed per-transfer results
    """

    total: int
    succeeded: int
    failed: int
    items: list[TransferItemResult] = field(default_factory=list)

    def all_succeeded(self) -> bool:
        """Check if all transfers succeeded.

        Returns:
            True if all transfers succeeded, False otherwise
        """
        return self.failed == 0


class TransferManager:
    """Orchestrates file transfers to multiple destination prefixes.

    Handles fan-out of local files to multiple destinations using rompy.transfer
    backends, with configurable failure policies and aggregated result tracking.
    """

    def transfer_files(
        self,
        files: list[Path],
        destinations: list[str],
        name_map: dict[Path, str],
        policy: TransferFailurePolicy = TransferFailurePolicy.CONTINUE,
    ) -> TransferBatchResult:
        """Transfer multiple files to multiple destination prefixes.

        For each file, computes the target name via name_map, then transfers
        to all destination prefixes. Destinations are treated as **prefixes**
        (folder-like), not complete object URIs.

        Final destination URI construction:
            dest_uri = join_prefix(dest_prefix, target_name)

        Example:
            files = [Path("restart.ww3"), Path("output.nc")]
            destinations = ["s3://bucket/outputs/", "file:///local/backup/"]
            name_map = {
                Path("restart.ww3"): "20230101_000000_restart.ww3",
                Path("output.nc"): "20230101_000000_output.nc"
            }

            Results in transfers to:
            - s3://bucket/outputs/20230101_000000_restart.ww3
            - s3://bucket/outputs/20230101_000000_output.nc
            - file:///local/backup/20230101_000000_restart.ww3
            - file:///local/backup/20230101_000000_output.nc

        Args:
            files: List of local file paths to transfer
            destinations: List of destination prefixes (e.g., "s3://bucket/path/")
            name_map: Mapping from local path to target filename
            policy: Failure handling policy (CONTINUE or FAIL_FAST)

        Returns:
            TransferBatchResult with aggregated success/failure counts and details

        Raises:
            Exception: On first failure if policy is FAIL_FAST
        """
        items: list[TransferItemResult] = []
        succeeded = 0
        failed = 0

        for local_path in files:
            target_name = name_map[local_path]

            for dest_prefix in destinations:
                dest_uri = join_prefix(dest_prefix, target_name)

                try:
                    transfer = get_transfer(dest_prefix)
                    transfer.put(local_path, dest_uri)

                    items.append(
                        TransferItemResult(
                            local_path=local_path,
                            dest_prefix=dest_prefix,
                            target_name=target_name,
                            dest_uri=dest_uri,
                            ok=True,
                            error=None,
                        )
                    )
                    succeeded += 1

                except Exception as e:
                    error_msg = f"{type(e).__name__}: {str(e)}"

                    items.append(
                        TransferItemResult(
                            local_path=local_path,
                            dest_prefix=dest_prefix,
                            target_name=target_name,
                            dest_uri=dest_uri,
                            ok=False,
                            error=error_msg,
                        )
                    )
                    failed += 1

                    if policy == TransferFailurePolicy.FAIL_FAST:
                        raise

        total = succeeded + failed
        return TransferBatchResult(
            total=total, succeeded=succeeded, failed=failed, items=items
        )
