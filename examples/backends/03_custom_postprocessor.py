"""A Pydantic v2 postprocessor using the public v2 protocol."""

import zipfile
from datetime import datetime, timezone
from pathlib import Path

from rompy.core.responses import (
    ArtifactType,
    LocalArtifact,
    PostprocessFailure,
    PostprocessSuccess,
    TimingInfo,
)
from rompy.postprocess import PostprocessContext


class ZipOutputsPostprocessor:
    """Context-aware postprocessor with explicit protocol capability."""

    name = "zip_outputs"
    input_protocol = "context"

    def process(self, context: PostprocessContext):
        start = datetime.now(timezone.utc)
        output_dir = context.output_dir or context.staging_dir
        if output_dir is None:
            return PostprocessFailure(
                run_id=context.run_result.run_id,
                error="postprocessor requires an output directory",
                artifacts=list(context.artifacts),
                expected_outputs=list(context.expected_outputs),
                missing_outputs=list(context.missing_outputs),
                timing=TimingInfo(start_time=start, end_time=datetime.now(timezone.utc)),
            )

        archive = output_dir / "outputs.zip"
        try:
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for source in sorted(output_dir.rglob("*")):
                    if source.is_file() and source != archive:
                        zip_file.write(source, source.relative_to(output_dir))
            artifact = LocalArtifact(
                path=archive.relative_to(output_dir).as_posix(),
                artifact_type=ArtifactType.OTHER,
                size_bytes=archive.stat().st_size,
            )
            return PostprocessSuccess(
                run_id=context.run_result.run_id,
                output_dir=str(output_dir),
                validated=True,
                artifacts=list(context.artifacts) + [artifact],
                expected_outputs=list(context.expected_outputs),
                missing_outputs=list(context.missing_outputs),
                file_count=1,
                message="Created outputs.zip",
                timing=TimingInfo(start_time=start, end_time=datetime.now(timezone.utc)),
            )
        except OSError as exc:
            return PostprocessFailure(
                run_id=context.run_result.run_id,
                error=f"could not create output archive: {exc}",
                output_dir=str(output_dir),
                artifacts=list(context.artifacts),
                expected_outputs=list(context.expected_outputs),
                missing_outputs=list(context.missing_outputs),
                timing=TimingInfo(start_time=start, end_time=datetime.now(timezone.utc)),
            )


def run_postprocessor(run_result, staging_dir: Path):
    """Standalone call: pass the typed ``processor_input`` result explicitly."""
    processor = ZipOutputsPostprocessor()
    context = PostprocessContext.from_run_result(run_result, staging_dir=staging_dir)
    return processor.process(context)
