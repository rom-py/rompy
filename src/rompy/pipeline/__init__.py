"""
Local pipeline backend for model execution.

This module provides the local pipeline backend implementation.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from rompy.backends import DockerConfig, LocalConfig
from rompy.core.responses import (
    GenerateFailure,
    ModelRunFailure,
    PipelineFailure,
    PipelineResult,
    PipelineStage,
    PipelineSuccess,
    PostprocessFailure,
    StageTiming,
    TimingInfo,
)

if TYPE_CHECKING:
    from rompy.backends.config import SlurmConfig
    from rompy.postprocess.config import BasePostprocessorConfig

logger = logging.getLogger(__name__)


def _exception_message(error: BaseException, fallback: str) -> str:
    """Preserve useful exception text while satisfying the failure contract."""
    message = str(error)
    return message if message.strip() else fallback


class LocalPipelineBackend:
    """Local pipeline backend that executes the full workflow locally.

    This backend uses the existing generate(), run() and postprocess() methods
    to execute the complete pipeline locally.
    """

    def execute(
        self,
        model_run,
        backend_config: Optional[
            Union[LocalConfig, DockerConfig, "SlurmConfig"]
        ] = None,
        processor: Optional["BasePostprocessorConfig"] = None,
        run_kwargs: Optional[Dict[str, Any]] = None,
        process_kwargs: Optional[Dict[str, Any]] = None,
        cleanup_on_failure: bool = False,
        validate_stages: bool = True,
        **kwargs,
    ) -> PipelineResult:
        """Execute the model pipeline locally.

        Args:
            model_run: The ModelRun instance to execute
            backend_config: Backend configuration object (LocalConfig, DockerConfig, etc.)
            processor: Processor configuration for the postprocess stage
            run_kwargs: Additional parameters for the run stage (deprecated, use backend_config)
            process_kwargs: Additional parameters for the postprocess stage
            cleanup_on_failure: Whether to cleanup outputs on pipeline failure
            validate_stages: Whether to validate each stage before proceeding
            **kwargs: Additional parameters (for backward compatibility)

        Returns:
            PipelineResult: Success or failure result with stage tracking, timing, and nested postprocess results.

            The result is a discriminated union:
            - PipelineSuccess: Contains stages_completed, nested postprocess_results, timing
            - PipelineFailure: Contains failed_stage, error, optional postprocess_results

        Raises:
            ValueError: If model_run is invalid or parameters are invalid
            TypeError: If processor is not a BasePostprocessorConfig instance

        Examples:
            ::

                from rompy.backends import LocalConfig
                from rompy.postprocess.config import NoopPostprocessorConfig

                backend = LocalPipelineBackend()
                result = backend.execute(
                    model_run=my_model,
                    backend_config=LocalConfig(timeout=3600),
                    processor=NoopPostprocessorConfig()
                )

                # Type-safe result handling with discriminated union
                if result.success:
                    # Type narrowing: result is PipelineSuccess
                    print(f"Stages: {[s.value for s in result.stages_completed]}")
                    print(f"Duration: {result.timing.duration_seconds}s")

                    # Access nested postprocess results
                    if result.postprocess_results and result.postprocess_results.success:
                        print(f"Artifacts: {len(result.postprocess_results.artifacts)}")
                else:
                    # Type narrowing: result is PipelineFailure
                    print(f"Failed at: {result.failed_stage.value}")
                    print(f"Error: {result.error}")

                # Serialize to dict for logging
                result_dict = result.model_dump()
        """
        from rompy.backends.config import BaseBackendConfig
        from rompy.postprocess.config import BasePostprocessorConfig, PostprocessPipelineConfig

        # Validate input parameters
        if not model_run:
            raise ValueError("model_run cannot be None")

        if not hasattr(model_run, "run_id"):
            raise ValueError("model_run must have a run_id attribute")

        if backend_config is None:
            raise ValueError(
                "backend_config is required. Provide a BackendConfig instance."
            )

        if not isinstance(backend_config, BaseBackendConfig):
            raise TypeError(
                f"backend_config must be a BaseBackendConfig instance, "
                f"got {type(backend_config).__name__}"
            )

        if processor is None:
            raise ValueError("processor configuration is required")

        if not isinstance(processor, (BasePostprocessorConfig, PostprocessPipelineConfig)):
            raise TypeError(
                f"processor must be a BasePostprocessorConfig instance or "
                f"PostprocessPipelineConfig, got {type(processor).__name__}"
            )

        # Initialize parameters
        process_kwargs = process_kwargs or {}
        start_time = datetime.now(timezone.utc)
        stages_completed: List[PipelineStage] = []
        stage_timings: List[StageTiming] = []
        cleaned_up = False
        staging_dir = None
        cleanup_error = None
        self._last_cleanup_error = None

        def cleanup_outputs():
            """Attempt cleanup without replacing the stage's primary error."""
            nonlocal cleaned_up, cleanup_error
            if not cleanup_on_failure:
                return
            try:
                cleaned_up = self._cleanup_outputs(staging_dir)
            except Exception as exc:  # pragma: no cover - defensive for custom cleaners
                cleaned_up = False
                cleanup_error = str(exc)
            cleanup_error = cleanup_error or getattr(self, "_last_cleanup_error", None)

        def stage_metadata(stage_result=None):
            metadata = {}
            if stage_result is not None:
                metadata["stage_result"] = stage_result.model_dump(mode="json")
            if cleanup_error:
                metadata["cleanup_error"] = cleanup_error
            return metadata

        def known_staging_path():
            if staging_dir is not None:
                return Path(staging_dir)
            try:
                candidate = getattr(model_run, "staging_dir", None)
                return Path(candidate) if candidate else None
            except (TypeError, ValueError):
                return None

        backend_type = backend_config.__class__.__name__.replace("Config", "").lower()
        processor_type = getattr(
            processor,
            "type",
            processor.__class__.__name__.replace("Config", "").lower(),
        )
        logger.info(f"Starting pipeline execution for run_id: {model_run.run_id}")
        logger.info(
            f"Pipeline configuration: backend='{backend_type}', processor='{processor_type}'"
        )

        try:
            # Stage 1: Generate input files
            logger.info(f"Stage 1: Generating input files for {model_run.run_id}")

            try:
                generate_result = model_run.generate()
                if not generate_result.success:
                    staging_dir = Path(generate_result.staging_dir) if generate_result.staging_dir else None
                    stage_timings.append(StageTiming(stage=PipelineStage.GENERATE, timing=generate_result.timing))
                    cleanup_outputs()
                    return PipelineFailure(
                        run_id=model_run.run_id, backend=backend_type, processor=processor_type,
                        stages_completed=[], failed_stage=PipelineStage.GENERATE,
                        staging_dir=str(staging_dir) if staging_dir else None,
                        error=generate_result.error,
                        generate_result=generate_result,
                        metadata=stage_metadata(generate_result),
                        stage_timings=stage_timings, timing=TimingInfo(start_time=start_time, end_time=datetime.now(timezone.utc)),
                        cleaned_up=cleaned_up,
                    )
                staging_dir = Path(generate_result.staging_dir)
                stage_timings.append(StageTiming(stage=PipelineStage.GENERATE, timing=generate_result.timing))
                logger.info(f"Input files generated successfully in: {staging_dir}")
            except Exception as e:
                logger.exception(f"Failed to generate input files: {e}")
                staging_dir = known_staging_path()
                generate_timing = TimingInfo(
                    start_time=start_time, end_time=datetime.now(timezone.utc)
                )
                error_message = _exception_message(e, "model generation failed")
                generate_failure = GenerateFailure(
                    run_id=model_run.run_id,
                    error=error_message,
                    generated_files=[],
                    staging_dir=str(staging_dir) if staging_dir else None,
                    timing=generate_timing,
                )
                stage_timings.append(
                    StageTiming(stage=PipelineStage.GENERATE, timing=generate_timing)
                )
                cleanup_outputs()
                return PipelineFailure(
                    run_id=model_run.run_id,
                    backend=backend_type,
                    processor=processor_type,
                    stages_completed=[],
                    failed_stage=PipelineStage.GENERATE,
                    staging_dir=str(staging_dir) if staging_dir else None,
                    error=generate_failure.error,
                    generate_result=generate_failure,
                    message=f"Input file generation failed: {error_message}",
                    metadata=stage_metadata(generate_failure),
                    stage_timings=stage_timings,
                    timing=TimingInfo(
                        start_time=start_time, end_time=datetime.now(timezone.utc)
                    ),
                    cleaned_up=cleaned_up,
                )

            # Validate generation stage
            if validate_stages:
                output_dir = Path(staging_dir)
                if not output_dir.exists():
                    logger.error(f"Output directory was not created: {output_dir}")
                    generate_timing = TimingInfo(
                        start_time=start_time, end_time=datetime.now(timezone.utc)
                    )
                    generate_failure = GenerateFailure(
                        run_id=model_run.run_id,
                        error=f"Output directory not found: {output_dir}",
                        generated_files=[],
                        staging_dir=str(staging_dir),
                        timing=generate_timing,
                    )
                    stage_timings.append(
                        StageTiming(stage=PipelineStage.GENERATE, timing=generate_timing)
                    )
                    cleanup_outputs()
                    return PipelineFailure(
                        run_id=model_run.run_id,
                        backend=backend_type,
                        processor=processor_type,
                        stages_completed=[],
                        failed_stage=PipelineStage.GENERATE,
                        staging_dir=str(staging_dir),
                        error=generate_failure.error,
                        generate_result=generate_failure,
                        message=f"Output directory not found after generation: {output_dir}",
                        metadata=stage_metadata(generate_failure),
                        stage_timings=stage_timings,
                        timing=TimingInfo(
                            start_time=start_time, end_time=datetime.now(timezone.utc)
                        ),
                        cleaned_up=cleaned_up,
                    )

            stages_completed.append(PipelineStage.GENERATE)
            # Stage 2: Run the model
            logger.info(f"Stage 2: Running model using {backend_type} backend")

            try:
                run_start = datetime.now(timezone.utc)
                # Pass the generated workspace directory to avoid duplicate generation
                run_result = model_run.run(
                    backend=backend_config, workspace_dir=staging_dir
                )

                if not run_result.success:
                    stage_timings.append(StageTiming(stage=PipelineStage.RUN, timing=run_result.timing))
                    logger.error("Model run failed")
                    cleanup_outputs()
                    return PipelineFailure(
                        success=False,
                        run_id=model_run.run_id,
                        backend=backend_type,
                        processor=processor_type,
                        stages_completed=stages_completed,
                        failed_stage=PipelineStage.RUN,
                        staging_dir=str(staging_dir),
                        workspace_dir=run_result.workspace_dir,
                        output_dir=run_result.output_dir,
                        error=run_result.error,
                        message=run_result.message or "Model run failed",
                        run_result=run_result,
                        metadata=stage_metadata(run_result),
                        stage_timings=stage_timings,
                        timing=TimingInfo(
                            start_time=start_time, end_time=datetime.now(timezone.utc)
                        ),
                        cleaned_up=cleaned_up,
                    )

                stage_timings.append(StageTiming(stage=PipelineStage.RUN, timing=run_result.timing))
                stages_completed.append(PipelineStage.RUN)
                logger.info("Model run completed successfully")

            except Exception as e:
                logger.exception(f"Error during model run: {e}")
                run_timing = TimingInfo(
                    start_time=run_start, end_time=datetime.now(timezone.utc)
                )
                error_message = _exception_message(e, "model execution failed")
                run_failure = ModelRunFailure(
                    run_id=model_run.run_id,
                    backend_used=backend_type,
                    error=error_message,
                    timing=run_timing,
                    output_dir=str(getattr(model_run, "output_dir", "")),
                    workspace_dir=str(staging_dir) if staging_dir else None,
                    artifacts=[],
                    expected_outputs=[],
                    missing_outputs=[],
                )
                stage_timings.append(
                    StageTiming(stage=PipelineStage.RUN, timing=run_timing)
                )
                cleanup_outputs()
                return PipelineFailure(
                    run_id=model_run.run_id,
                    backend=backend_type,
                    processor=processor_type,
                    stages_completed=stages_completed,
                    failed_stage=PipelineStage.RUN,
                    staging_dir=str(staging_dir),
                    workspace_dir=str(staging_dir),
                    message=f"Model run error: {error_message}",
                    error=run_failure.error,
                    run_result=run_failure,
                    metadata=stage_metadata(run_failure),
                    timing=TimingInfo(
                        start_time=start_time, end_time=datetime.now(timezone.utc)
                    ),
                    stage_timings=stage_timings,
                    cleaned_up=cleaned_up,
                )

            # Stage 3: Postprocess outputs
            logger.info(f"Stage 3: Postprocessing with {processor_type}")
            postprocess_start = datetime.now(timezone.utc)

            try:
                postprocess_results = model_run.postprocess(
                    processor=processor, processor_input=run_result, **process_kwargs
                )

                # Check if postprocessing was successful
                if isinstance(postprocess_results, PostprocessFailure):
                    stage_timings.append(StageTiming(stage=PipelineStage.POSTPROCESS, timing=postprocess_results.timing))
                    cleanup_outputs()
                    logger.warning(
                        "Postprocessing failed but pipeline will mark as complete with failure"
                    )
                    # Return PipelineFailure with nested PostprocessFailure
                    return PipelineFailure(
                        success=False,
                        run_id=model_run.run_id,
                        backend=backend_type,
                        processor=processor_type,
                        stages_completed=stages_completed,
                        failed_stage=PipelineStage.POSTPROCESS,
                        staging_dir=str(staging_dir),
                        output_dir=postprocess_results.output_dir,
                        message=f"Postprocessing failed: {postprocess_results.message}",
                        error=postprocess_results.error,
                        postprocess_results=postprocess_results,
                        metadata=stage_metadata(postprocess_results),
                        stage_timings=stage_timings,
                        timing=TimingInfo(
                            start_time=start_time, end_time=datetime.now(timezone.utc)
                        ),
                        cleaned_up=cleaned_up,
                    )

                stage_timings.append(StageTiming(stage=PipelineStage.POSTPROCESS, timing=postprocess_results.timing))
                stages_completed.append(PipelineStage.POSTPROCESS)
                logger.info("Postprocessing completed")

            except Exception as e:
                logger.exception(f"Error during postprocessing: {e}")
                postprocess_timing = TimingInfo(start_time=postprocess_start, end_time=datetime.now(timezone.utc))
                stage_timings.append(StageTiming(stage=PipelineStage.POSTPROCESS, timing=postprocess_timing))
                error_message = _exception_message(e, "postprocessing failed")
                postprocess_failure = PostprocessFailure(
                    run_id=model_run.run_id,
                    error=error_message,
                    output_dir=str(staging_dir) if staging_dir else None,
                    timing=postprocess_timing,
                    artifacts=[],
                    expected_outputs=[],
                    missing_outputs=[],
                )
                cleanup_outputs()
                return PipelineFailure(
                    run_id=model_run.run_id,
                    backend=backend_type,
                    processor=processor_type,
                    stages_completed=stages_completed,
                    failed_stage=PipelineStage.POSTPROCESS,
                    staging_dir=str(staging_dir),
                    output_dir=postprocess_failure.output_dir,
                    message=f"Postprocessing error: {error_message}",
                    error=postprocess_failure.error,
                    postprocess_results=postprocess_failure,
                    metadata=stage_metadata(postprocess_failure),
                    stage_timings=stage_timings,
                    timing=TimingInfo(
                        start_time=start_time, end_time=datetime.now(timezone.utc)
                    ),
                    cleaned_up=cleaned_up,
                )

            # Pipeline completed successfully
            logger.info(
                f"Pipeline execution completed successfully for run_id: {model_run.run_id}"
            )

            # Compute output_dir for successful pipeline
            output_dir_path = Path(run_result.output_dir)

            return PipelineSuccess(
                success=True,
                run_id=model_run.run_id,
                backend=backend_type,
                processor=processor_type,
                stages_completed=stages_completed,
                staging_dir=str(staging_dir),
                output_dir=str(output_dir_path),
                postprocess_results=postprocess_results,
                stage_timings=stage_timings,
                message="Pipeline completed successfully",
                timing=TimingInfo(
                    start_time=start_time, end_time=datetime.now(timezone.utc)
                ),
            )

        except Exception as e:
            logger.exception(f"Unexpected error in pipeline execution: {e}")
            failed_stage = (
                PipelineStage.GENERATE if PipelineStage.GENERATE not in stages_completed
                else PipelineStage.RUN if PipelineStage.RUN not in stages_completed
                else PipelineStage.POSTPROCESS
            )
            attempted_timing = TimingInfo(
                start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc)
            )
            error_message = _exception_message(
                e,
                {
                    PipelineStage.GENERATE: "model generation failed",
                    PipelineStage.RUN: "model execution failed",
                    PipelineStage.POSTPROCESS: "postprocessing failed",
                }[failed_stage],
            )
            nested = {}
            if failed_stage is PipelineStage.GENERATE:
                nested["generate_result"] = GenerateFailure(
                    run_id=model_run.run_id, error=error_message, generated_files=[],
                    staging_dir=str(staging_dir) if staging_dir else None,
                    timing=attempted_timing,
                )
            elif failed_stage is PipelineStage.RUN:
                nested["run_result"] = ModelRunFailure(
                    run_id=model_run.run_id, backend_used=backend_type, error=error_message,
                    timing=attempted_timing, output_dir=str(getattr(model_run, "output_dir", "")),
                    workspace_dir=str(staging_dir) if staging_dir else None,
                    artifacts=[], expected_outputs=[], missing_outputs=[],
                )
            else:
                nested["postprocess_results"] = PostprocessFailure(
                    run_id=model_run.run_id, error=error_message, timing=attempted_timing,
                    output_dir=str(staging_dir) if staging_dir else None,
                    artifacts=[], expected_outputs=[], missing_outputs=[],
                )
            stage_timings.append(StageTiming(stage=failed_stage, timing=attempted_timing))
            cleanup_outputs()
            return PipelineFailure(
                run_id=model_run.run_id,
                backend=backend_type,
                processor=processor_type,
                stages_completed=stages_completed[: list(PipelineStage).index(failed_stage)],
                failed_stage=failed_stage,
                staging_dir=str(staging_dir) if staging_dir else None,
                message=f"Pipeline error: {error_message}",
                error=error_message,
                metadata=stage_metadata(next(iter(nested.values()))),
                stage_timings=stage_timings,
                timing=TimingInfo(
                    start_time=start_time, end_time=datetime.now(timezone.utc)
                ),
                cleaned_up=cleaned_up,
                **nested,
            )

    def _cleanup_outputs(self, output_dir) -> bool:
        """Clean the actual generated path and report the confirmed outcome."""
        self._last_cleanup_error = None
        if output_dir is None:
            return False
        try:
            output_dir = Path(output_dir)
            if not output_dir.exists():
                return True
            logger.info(f"Cleaning up output directory: {output_dir}")
            import shutil
            shutil.rmtree(output_dir)
            return not output_dir.exists()
        except Exception as e:
            self._last_cleanup_error = _exception_message(e, "cleanup failed")
            logger.warning(f"Failed to cleanup output directory: {e}")
            return False
