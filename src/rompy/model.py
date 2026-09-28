"""
Model run implementation for ROMPY.

This module provides the ModelRun class which is the main entry point for
running models with ROMPY.
"""

import hashlib
import os
import platform
import shutil
import zipfile as zf
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Union

from pydantic import Field, TypeAdapter

from rompy.backends import BackendConfig
from rompy.backends.config import BaseBackendConfig
from rompy.core.config import BaseConfig
from rompy.core.responses import (
    GenerateFailure,
    GenerateResult,
    GenerateResultSidecar,
    GenerateSuccess,
    ModelRunFailure,
    ModelRunResult,
    ModelRunSuccess,
    NormalizedContext,
    PipelineResult,
    PostprocessFailure,
    PostprocessResult,
    PostprocessResultSidecar,
    PostprocessSuccess,
    RunResultSidecar,
    TimingInfo,
)
from rompy.core.time import TimeRange
from rompy.core.types import RompyBaseModel
from rompy.logging import get_logger
from rompy.utils import load_entry_points

# Initialize the logger
logger = get_logger(__name__)


# Accepted config types are defined in the entry points of the rompy.config group
CONFIG_TYPES = load_entry_points("rompy.config")
# ``typing.Union[()]`` raises during class creation when no plugins are
# installed.  BaseConfig is the bounded core-safe fallback; installed plugin
# types remain available for normal configuration loading.
CONFIG_TYPES = CONFIG_TYPES or (BaseConfig,)


def _load_backends():
    """Load backends from entry points with fallback handling."""
    run_backends = {}
    postprocessors = {}
    pipeline_backends = {}

    # Load run backends
    try:
        for backend in load_entry_points("rompy.run"):
            name = backend.__name__.lower().replace("runbackend", "")
            run_backends[name] = backend
    except Exception as e:
        logger.warning(f"Failed to load run backends: {e}")

    # Load postprocessors
    try:
        for proc in load_entry_points("rompy.postprocess"):
            name = proc.__name__.lower().replace("postprocessor", "")
            postprocessors[name] = proc
    except Exception as e:
        logger.warning(f"Failed to load postprocessors: {e}")

    # Load pipeline backends
    try:
        for backend in load_entry_points("rompy.pipeline"):
            name = backend.__name__.lower().replace("pipelinebackend", "")
            pipeline_backends[name] = backend
    except Exception as e:
        logger.warning(f"Failed to load pipeline backends: {e}")

    return run_backends, postprocessors, pipeline_backends


# Load backends from entry points
RUN_BACKENDS, POSTPROCESSORS, PIPELINE_BACKENDS = _load_backends()


def _exception_message(error: BaseException, fallback: str) -> str:
    """Preserve useful exception text while satisfying the failure contract."""
    message = str(error)
    return message if message.strip() else fallback


def _make_model_run_result(**data):
    """Construct the concrete result variant at the runtime boundary."""
    data.setdefault("artifacts", [])
    data.setdefault("expected_outputs", [])
    data.setdefault("missing_outputs", [])
    variant = ModelRunSuccess if data.get("success") else ModelRunFailure
    if data.get("success"):
        data.pop("error", None)
    elif not isinstance(data.get("error"), str) or not data["error"].strip():
        data["error"] = "model execution failed"
    return variant(**data)


def _backend_metadata(backend: BaseBackendConfig) -> dict[str, Any]:
    """Return only non-sensitive backend metadata for persisted results.

    Backend configuration contains arbitrary environment variables and, for
    Docker, arbitrary build arguments.  Neither is safe to persist because the
    values may contain credentials.  Keep the stable type and resource limit
    useful to consumers without copying execution configuration wholesale.
    """
    return {
        "type": type(backend).__name__,
        "timeout": backend.timeout,
    }


class ModelRun(RompyBaseModel):
    """A model run.

    It is intented to be model agnostic.
    It deals primarily with how the model is to be run, i.e. the period of the run
    and where the output is going. The actual configuration of the run is
    provided by the config object.

    Further explanation is given in the rompy.core.Baseconfig docstring.
    """

    # Initialize formatting variables in __init__

    model_type: Literal["modelrun"] = Field("modelrun", description="The model type.")
    run_id: str = Field("run_id", description="The run id")
    period: TimeRange = Field(
        TimeRange(
            start=datetime(2020, 2, 21, 4),
            end=datetime(2020, 2, 24, 4),
            interval="15M",
        ),
        description="The time period to run the model",
    )
    output_dir: Path = Field("./simulations", description="The output directory")
    config: Union[CONFIG_TYPES] = Field(
        default_factory=BaseConfig,
        description="The configuration object",
        discriminator="model_type",
    )
    delete_existing: bool = Field(False, description="Delete existing output directory")
    run_id_subdir: bool = Field(
        True, description="Use run_id subdirectory in the output directory"
    )
    _datefmt: str = "%Y%m%d.%H%M%S"
    _staging_dir: Path = None

    @property
    def staging_dir(self):
        """The directory where the model is staged for execution

        returns
        -------
        staging_dir : str
        """

        if self._staging_dir is None:
            self._staging_dir = self._create_staging_dir()
        return self._staging_dir

    def _create_staging_dir(self):
        if self.run_id_subdir:
            odir = Path(self.output_dir) / self.run_id
        else:
            odir = Path(self.output_dir)
        if self.delete_existing and odir.exists():
            shutil.rmtree(odir)
        odir.mkdir(parents=True, exist_ok=True)
        return odir

    @property
    def _generation_medatadata(self):
        return dict(
            _generated_at=str(datetime.now(timezone.utc)),
            _generated_by=os.environ.get("USER"),
            _generated_on=platform.node(),
        )

    def _compute_config_hash(self, staging_dir: Path) -> str:
        """Compute SHA256 hash of all files in staging_dir.

        Files are sorted by path to ensure deterministic hash.
        Returns empty string if no files exist or on any IO error.
        """
        try:
            from rompy.core.result_persistence import GENERATE_RESULT_FILENAME

            files = sorted(staging_dir.iterdir(), key=lambda f: str(f))
            files = [
                f for f in files if f.is_file() and f.name != GENERATE_RESULT_FILENAME
            ]

            if not files:
                return ""

            hasher = hashlib.sha256()
            for file_path in files:
                hasher.update(file_path.read_bytes())

            return hasher.hexdigest()
        except Exception:
            return ""

    def _normalized_context(self, staging_dir: Path) -> NormalizedContext:
        """Build the canonical context used by all operation sidecars."""
        start = self.period.start
        end = self.period.end
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        else:
            start = start.astimezone(timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        else:
            end = end.astimezone(timezone.utc)
        return NormalizedContext(
            model_type=getattr(self.config, "model_type", type(self.config).__name__.lower()),
            period_start=start,
            period_end=end,
            period_interval=self.period.interval.total_seconds(),
            output_dir=str(self.output_dir),
            staging_dir=str(staging_dir),
            config_hash=self._compute_config_hash(staging_dir),
            extensions=self._get_normalized_extensions(),
        )

    def generate(self) -> GenerateResult:
        """Generate the model input files

        returns
        -------
        staging_dir : str

        """
        start_time = datetime.now(timezone.utc)
        # Import formatting utilities
        from rompy.formatting import log_box

        # Keep presentation independent from the structured values used below.
        # Parsing rendered rows is incorrect in ASCII mode (which uses ``|``
        # rather than the Unicode ``┃`` separator).
        config_type = type(self.config).__name__
        duration = self.period.end - self.period.start
        formatted_duration = self.period.format_duration(duration)

        rows = [
            ("Run ID", str(self.run_id)),
            ("Model Type", config_type),
            ("Start Time", self.period.start.isoformat()),
            ("End Time", self.period.end.isoformat()),
            ("Duration", formatted_duration),
            ("Time Interval", str(self.period.interval)),
            ("Output Directory", str(self.output_dir)),
        ]

        if hasattr(self.config, "description") and self.config.description:
            rows.append(("Description", self.config.description))

        max_key_len = max(len(key) for key, _ in rows)
        aligned_rows = [
            f"{key:>{max_key_len}} : {value}" for key, value in rows
        ]

        # Log the box with the model run info
        log_box(title="MODEL RUN CONFIGURATION", logger=logger, add_empty_line=False)

        # Log each row of the content with proper indentation
        for row in aligned_rows:
            logger.info(f"  {row}")

        # Log the bottom of the box
        log_box(
            title=None,
            logger=logger,
            add_empty_line=True,  # Just the bottom border
        )

        # Display detailed configuration info using the new formatting framework
        from rompy.formatting import log_box

        # Create a box with the configuration type as title
        log_box(f"MODEL CONFIGURATION ({config_type})")

        # Use the model's string representation which now uses the new formatting
        try:
            # The __str__ method of RompyBaseModel already handles the formatting
            config_str = str(self.config)
            for line in config_str.split("\n"):
                logger.info(line)
        except Exception as e:
            # If anything goes wrong with config formatting, log the error and minimal info
            logger.info(f"Using {type(self.config).__name__} configuration")
            logger.debug(f"Configuration string formatting error: {str(e)}")

        logger.info("")
        log_box(
            title="STARTING MODEL GENERATION",
            logger=logger,
            add_empty_line=False,
        )
        logger.info(f"Preparing input files in {self.output_dir}")

        try:
            # Collect context data
            cc_full = {}
            cc_full["runtime"] = self.model_dump()
            cc_full["runtime"]["staging_dir"] = self.staging_dir
            cc_full["runtime"].update(self._generation_medatadata)
            cc_full["runtime"].update({"_datefmt": self._datefmt})

            # Process configuration
            logger.info("Processing model configuration...")
            if callable(self.config):
                # Run the __call__() method of the config object if it is callable passing
                # the runtime instance, and fill in the context with what is returned
                logger.info("Running configuration callable...")
                cc_full["config"] = self.config(self)
            else:
                # Otherwise just fill in the context with the config instance itself
                logger.info("Using static configuration...")
                cc_full["config"] = self.config

            # Render templates
            logger.info(f"Rendering model configurations to {self.staging_dir}...")
            self.config.render(cc_full, self.output_dir)

            logger.info("")
            # Use the log_box utility function
            from rompy.formatting import log_box

            log_box(
                title="MODEL GENERATION COMPLETE",
                logger=logger,
                add_empty_line=False,
            )
            logger.info(f"Model files generated at: {self.staging_dir}")

            generated_files = [
                str(f.relative_to(self.staging_dir).as_posix())
                for f in self.staging_dir.rglob("*")
                if f.is_file()
            ]
            result = GenerateSuccess(
                run_id=self.run_id,
                staging_dir=str(self.staging_dir),
                generated_files=generated_files,
                timing=TimingInfo(start_time=start_time, end_time=datetime.now(timezone.utc)),
            )
            normalized_ctx = self._normalized_context(self.staging_dir)
            sidecar = GenerateResultSidecar(
                created_at=datetime.now(timezone.utc),
                run_id=self.run_id,
                staging_dir=str(self.staging_dir),
                status="success",
                success=True,
                payload=result,
                normalized_context=normalized_ctx,
            )
            from rompy.core.result_persistence import persist_result
            persisted = persist_result(result, sidecar, self.staging_dir)
            if isinstance(persisted, GenerateFailure):
                return persisted
            return persisted

        except Exception as e:
            staging_dir = self._staging_dir
            result = GenerateFailure(
                run_id=self.run_id,
                error=_exception_message(e, "model generation failed"),
                generated_files=(
                    [str(f.relative_to(staging_dir).as_posix()) for f in staging_dir.rglob("*") if f.is_file()]
                    if staging_dir is not None and staging_dir.exists() else []
                ),
                timing=TimingInfo(start_time=start_time, end_time=datetime.now(timezone.utc)),
                staging_dir=str(staging_dir) if staging_dir is not None else None,
            )
            if staging_dir is not None:
                sidecar = GenerateResultSidecar(
                    created_at=datetime.now(timezone.utc),
                    run_id=self.run_id,
                    staging_dir=str(staging_dir),
                    status="failed",
                    success=False,
                    error=result.error,
                    payload=result,
                    normalized_context=self._normalized_context(staging_dir),
                )
                from rompy.core.result_persistence import persist_result
                return persist_result(result, sidecar, staging_dir, primary_error=result.error)
            return result

    def zip(self) -> str:
        """Zip the input files for the model run

        This function zips the input files for the model run and returns the
        name of the zip file. It also cleans up the staging directory leaving
        only the settings.json file that can be used to reproduce the run.

        returns
        -------
        zip_fn : str
        """
        # Use the log_box utility function
        from rompy.formatting import log_box

        log_box(
            title="ARCHIVING MODEL FILES",
            logger=logger,
        )

        # Always remove previous zips
        zip_fn = Path(str(self.staging_dir) + ".zip")
        if zip_fn.exists():
            logger.info(f"Removing existing archive at {zip_fn}")
            zip_fn.unlink()

        # Count files to be archived
        file_count = sum([len(fn) for _, _, fn in os.walk(self.staging_dir)])
        logger.info(f"Archiving {file_count} files from {self.staging_dir}")

        # Create zip archive
        with zf.ZipFile(zip_fn, mode="w", compression=zf.ZIP_DEFLATED) as z:
            for dp, dn, fn in os.walk(self.staging_dir):
                for filename in fn:
                    source_path = os.path.join(dp, filename)
                    rel_path = os.path.relpath(source_path, self.staging_dir)
                    z.write(source_path, rel_path)

        # Clean up staging directory
        logger.info(f"Cleaning up staging directory {self.staging_dir}")
        shutil.rmtree(self.staging_dir)

        from rompy.formatting import log_box

        log_box(
            f"✓ Archive created successfully: {zip_fn}",
            logger=logger,
            add_empty_line=False,
        )
        return zip_fn

    def __call__(self):
        return self.generate()

    def _get_normalized_extensions(self) -> Dict[str, Any]:
        get_extensions = getattr(self.config, "get_normalized_extensions", None)
        if callable(get_extensions):
            try:
                extensions = get_extensions()
                if isinstance(extensions, dict):
                    return extensions
            except Exception:
                pass
        return {}

    def _compute_run_normalized_context(
        self, workspace_dir: Optional[str]
    ) -> NormalizedContext:
        """Compute normalized context for run sidecars.

        Tries to copy normalized_context from generate_result.json if present,
        otherwise computes fallback from model fields.

        Args:
            workspace_dir: Workspace directory path (may be None)

        Returns:
            NormalizedContext for inclusion in RunResultSidecar
        """
        normalized_ctx = None

        # Try to copy from generate_result.json if workspace exists
        if workspace_dir:
            try:
                from rompy.core.result_persistence import load_generate_result

                gen_result = load_generate_result(Path(workspace_dir))
                if gen_result.normalized_context is not None:
                    normalized_ctx = gen_result.normalized_context
            except (FileNotFoundError, Exception):
                pass

        # Fallback: compute from model fields if not found or no workspace
        if normalized_ctx is None:
            normalized_ctx = self._normalized_context(
                Path(workspace_dir) if workspace_dir else Path(self.output_dir)
            )

        return normalized_ctx

    def run(
        self, backend: BackendConfig, workspace_dir: Optional[str] = None
    ) -> ModelRunResult:
        """
        Run the model using the specified backend configuration.

        This method uses Pydantic configuration objects that provide type safety
        and validation for all backend parameters. It returns a structured
        ``ModelRunResult`` with timing information, metadata, and detailed error
        messages.

        Args:
            backend: Pydantic configuration object (LocalConfig, DockerConfig, etc.)
            workspace_dir: Path to generated workspace directory (optional)

        Returns:
            ModelRunResult: Structured result object with success status, timing,
                backend information, and error details (if applicable).

        Examples:
            ::

                from rompy.backends import LocalConfig, DockerConfig

                # Local execution
                result = model.run(LocalConfig(timeout=3600, command="python run.py"))
                if result.success:
                    print(f"Completed in {result.timing.duration_seconds}s")

                # Docker execution
                result = model.run(DockerConfig(image="swan:latest", cpu=4, memory="2g"))
                if not result.success:
                    print(f"Failed: {result.error}")
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Validate backend type
            if not isinstance(backend, BaseBackendConfig):
                result = _make_model_run_result(
                    success=False,
                    run_id=self.run_id,
                    backend_used=type(backend).__name__,
                    output_dir=str(self.output_dir),
                    workspace_dir=workspace_dir,
                    error=f"Backend must be a subclass of BaseBackendConfig, got {type(backend).__name__}",
                    message="Invalid backend configuration",
                    timing=TimingInfo(
                        start_time=start_time,
                        end_time=datetime.now(timezone.utc),
                    ),
                )

                # Write run_result.json sidecar
                if workspace_dir:
                    from rompy.core.result_persistence import persist_result

                    normalized_ctx = self._compute_run_normalized_context(workspace_dir)

                    sidecar = RunResultSidecar(
                        created_at=datetime.now(timezone.utc),
                        updated_at=None,
                        run_id=result.run_id,
                        staging_dir=str(workspace_dir),
                        status="failed",
                        success=False,
                        error=result.error,
                        normalized_context=normalized_ctx,
                        payload=result,
                    )
                    result = persist_result(result, sidecar, Path(workspace_dir))

                return result

            logger.debug(f"Using backend config: {type(backend).__name__}")

            # Dispatch directly to the backend
            backend_class = backend.get_backend_class()
            backend_instance = backend_class()
            success = backend_instance.run(
                self, config=backend, workspace_dir=workspace_dir
            )
            generation_failure = getattr(backend_instance, "generate_result", None)
            if isinstance(generation_failure, GenerateFailure):
                success = False

            # Derive one authoritative workspace from the typed generation result.
            effective_workspace = Path(workspace_dir) if workspace_dir else None
            if effective_workspace is None and generation_failure is not None:
                effective_workspace = Path(generation_failure.staging_dir) if generation_failure.staging_dir else None
            if effective_workspace is None:
                generated = getattr(backend_instance, "generate_result", None)
                if isinstance(generated, GenerateSuccess):
                    effective_workspace = Path(generated.staging_dir)

            output_dir_path: Optional[Path] = None
            if self.output_dir:
                output_dir_path = Path(self.output_dir)
                if self.run_id_subdir:
                    output_dir_path = output_dir_path / self.run_id
            output_dir_str = str(output_dir_path) if output_dir_path else str(self.output_dir)
            workspace_dir_str = str(effective_workspace) if effective_workspace else None
            backend_class_name = type(backend).__name__.replace("Config", "")
            artifacts = []
            expected_outputs = []
            missing_outputs = []
            if output_dir_str:
                discovered = self.config.validate_outputs(output_dir_str) if success else []
                root = Path(output_dir_str).resolve()
                for artifact in discovered:
                    if getattr(artifact, "kind", "local") == "remote":
                        artifacts.append(artifact)
                        continue
                    candidate = Path(artifact.path)
                    if candidate.is_absolute():
                        try:
                            candidate = candidate.resolve().relative_to(root)
                        except ValueError as exc:
                            raise ValueError(f"observed artifact is outside output root: {artifact.path}") from exc
                    else:
                        candidate = Path(str(candidate))
                    artifacts.append(artifact.model_copy(update={"path": candidate.as_posix()}))
                declared = self.config.expected_artifacts() if success else []
                for artifact in declared:
                    if getattr(artifact, "kind", "local") == "remote":
                        expected = artifact
                    else:
                        candidate = Path(artifact.path)
                        if candidate.is_absolute():
                            try:
                                candidate = candidate.resolve().relative_to(root)
                            except ValueError as exc:
                                raise ValueError(f"expected artifact is outside output root: {artifact.path}") from exc
                        expected = artifact.model_copy(update={"path": candidate.as_posix()})
                    expected_outputs.append(expected)
                def _identity(item):
                    return (item.kind, item.path) if item.kind == "local" else (item.kind, item.uri)

                observed_ids = {_identity(item) for item in artifacts}
                missing_outputs = [item for item in expected_outputs if _identity(item) not in observed_ids]

            run_context = self._compute_run_normalized_context(str(effective_workspace)) if effective_workspace else None
            result = _make_model_run_result(
                success=success,
                run_id=self.run_id,
                backend_used=backend_class_name,
                output_dir=output_dir_str,
                workspace_dir=workspace_dir_str,
                artifacts=artifacts,
                expected_outputs=expected_outputs,
                missing_outputs=missing_outputs,
                error=(generation_failure.error if isinstance(generation_failure, GenerateFailure) else None),
                message=(
                    "Model execution completed successfully"
                    if success
                    else (generation_failure.error if isinstance(generation_failure, GenerateFailure) else "Model execution failed")
                ),
                timing=TimingInfo(
                    start_time=start_time,
                    end_time=datetime.now(timezone.utc),
                ),
                metadata={
                    "backend_config": _backend_metadata(backend),
                    **({"generate_result": generation_failure.model_dump(mode="json")} if isinstance(generation_failure, GenerateFailure) else {}),
                    **({"normalized_context": run_context.model_dump(mode="json")} if run_context is not None else {}),
                },
            )

            # Write run_result.json sidecar
            if effective_workspace:
                from rompy.core.result_persistence import persist_result

                normalized_ctx = run_context or self._compute_run_normalized_context(str(effective_workspace))

                sidecar = RunResultSidecar(
                    created_at=datetime.now(timezone.utc),
                    updated_at=None,
                    run_id=result.run_id,
                    staging_dir=str(effective_workspace),
                    status="success" if result.success else "failed",
                    success=result.success,
                    error=result.error if not result.success else None,
                    normalized_context=normalized_ctx,
                    payload=result,
                )
                result = persist_result(result, sidecar, effective_workspace)

            return result

        except Exception as e:
            # A backend may generate implicitly before raising.  Recover that
            # typed generation path so the failure remains durable and useful.
            known_workspace = locals().get("effective_workspace")
            if known_workspace is None and workspace_dir:
                known_workspace = Path(workspace_dir)
            if known_workspace is None:
                generated = locals().get("backend_instance")
                generated_result = getattr(generated, "generate_result", None)
                if isinstance(generated_result, (GenerateSuccess, GenerateFailure)):
                    known_workspace = (
                        Path(generated_result.staging_dir)
                        if generated_result.staging_dir
                        else None
                    )
            workspace_dir_str = str(known_workspace) if known_workspace else None
            normalized_ctx = (
                self._compute_run_normalized_context(workspace_dir_str)
                if workspace_dir_str
                else None
            )

            output_dir_path = Path(self.output_dir) if self.output_dir else None
            if output_dir_path is not None and self.run_id_subdir:
                output_dir_path = output_dir_path / self.run_id
            error_message = _exception_message(e, "model execution failed")
            result = _make_model_run_result(
                success=False,
                run_id=self.run_id,
                backend_used=(
                    type(backend).__name__.replace("Config", "")
                    if isinstance(backend, BaseBackendConfig)
                    else "unknown"
                ),
                output_dir=str(output_dir_path) if output_dir_path else str(self.output_dir),
                workspace_dir=workspace_dir_str,
                error=error_message,
                message=f"Model execution failed with exception: {error_message}",
                timing=TimingInfo(
                    start_time=start_time,
                    end_time=datetime.now(timezone.utc),
                ),
                metadata=(
                    {"normalized_context": normalized_ctx.model_dump(mode="json")}
                    if normalized_ctx is not None
                    else {}
                ),
            )

            # Write run_result.json sidecar at the recovered generated path.
            if known_workspace:
                from rompy.core.result_persistence import persist_result

                normalized_ctx = normalized_ctx or self._compute_run_normalized_context(
                    str(known_workspace)
                )
                sidecar = RunResultSidecar(
                    created_at=datetime.now(timezone.utc),
                    updated_at=None,
                    run_id=result.run_id,
                    staging_dir=str(known_workspace),
                    status="failed",
                    success=False,
                    error=result.error,
                    normalized_context=normalized_ctx,
                    payload=result,
                )
                result = persist_result(
                    result,
                    sidecar,
                    known_workspace,
                    primary_error=result.error,
                )

            return result

    def postprocess(
        self,
        processor,
        processor_input=None,
        **kwargs,
    ) -> PostprocessResult:
        """
        Postprocess the model outputs using the specified processor configuration.

        This method uses the provided configuration to instantiate and execute
        the appropriate postprocessor. The processor type is determined by the
        configuration object.

        Args:
            processor: Configuration object for the postprocessor to use
            **kwargs: Additional processor-specific parameters (override config values)

        Returns:
            PostprocessResult: Typed result object with success status, timing,
                and artifacts (for success) or error details (for failure).

                The result is a discriminated union:
                - PostprocessSuccess: Contains artifacts list, output_dir, timing
                - PostprocessFailure: Contains error message, timing

        Raises:
            TypeError: If processor is not a BasePostprocessorConfig instance

        Examples:
            ::

                from rompy.postprocess.config import NoopPostprocessorConfig

                # Run postprocessing
                result = model.postprocess(NoopPostprocessorConfig())

                # Type-safe result handling with discriminated union
                if result.success:
                    # Type narrowing: result is PostprocessSuccess
                    print(f"Generated {len(result.artifacts)} artifacts")
                    for artifact in result.artifacts:
                        print(f"  {artifact.type.value}: {artifact.path}")
                    print(f"Completed in {result.timing.duration_seconds}s")
                else:
                    # Type narrowing: result is PostprocessFailure
                    print(f"Failed: {result.error}")
                    print(f"Message: {result.message}")

                # Serialize to dict for logging or storage
                result_dict = result.model_dump()
        """
        from rompy.postprocess.config import (
            BasePostprocessorConfig,
            PostprocessPipelineConfig,
        )

        start_time = datetime.now(timezone.utc)

        try:
            if isinstance(processor, PostprocessPipelineConfig):
                if processor_input is None:
                    raise TypeError("processor_input must be a validated ModelRunResult")
                run_result = TypeAdapter(ModelRunResult).validate_python(processor_input)
                from rompy.postprocess.runner import run_postprocess_pipeline
                return run_postprocess_pipeline(
                    run_result,
                    processor.build_steps(),
                    staging_dir=self.staging_dir,
                    failure_policy=processor.failure_policy,
                    operational_state=processor.operational_state,
                )
            if not isinstance(processor, BasePostprocessorConfig):
                raise TypeError(
                    f"processor must be a BasePostprocessorConfig instance, got {type(processor).__name__}"
                )
            if processor_input is None:
                raise TypeError("processor_input must be a validated ModelRunResult")
            if not isinstance(processor_input, (ModelRunSuccess, ModelRunFailure)):
                raise TypeError("processor_input must be a concrete ModelRunSuccess or ModelRunFailure")
            run_result = TypeAdapter(ModelRunResult).validate_python(processor_input)
            processor_instance = processor.build_processor()
            # Options are explicit process options, never flattened constructor state.
            process_options = dict(kwargs)
            legacy_adapter = getattr(processor_instance, "process_legacy", None)
            if callable(legacy_adapter):
                # Built-ins such as transfer expose this seam because their
                # composable API consumes PostprocessContext.
                process_options.setdefault("staging_dir", self.staging_dir)
                result = legacy_adapter(run_result, **process_options)
            elif getattr(processor_instance, "input_protocol", None) == "context":
                from rompy.postprocess.protocol import PostprocessContext
                context = PostprocessContext.from_run_result(
                    run_result, staging_dir=self.staging_dir
                )
                result = processor_instance.process(context, **process_options)
            else:
                # Unmarked plugins are the legacy public ModelRunResult seam;
                # their class or entry-point name is not part of dispatch.
                result = processor_instance.process(run_result, **process_options)
            if not isinstance(result, (PostprocessSuccess, PostprocessFailure)):
                raise TypeError("processor output must be a concrete PostprocessSuccess or PostprocessFailure")
            result = TypeAdapter(PostprocessResult).validate_python(result)
            sidecar = PostprocessResultSidecar(
                created_at=datetime.now(timezone.utc),
                run_id=run_result.run_id,
                staging_dir=str(self.staging_dir),
                status="success" if result.success else "failed",
                success=result.success,
                error=None if result.success else result.error,
                payload=result,
            )
            from rompy.core.result_persistence import persist_result
            return persist_result(result, sidecar, Path(self.staging_dir),
                                  primary_error=None if result.success else result.error)
        except Exception as e:
            result = PostprocessFailure(
                run_id=self.run_id,
                output_dir=str(self.staging_dir),
                message=f"Postprocessing failed: {e}",
                error=f"Processor protocol failure: {e}",
                artifacts=[], expected_outputs=[], missing_outputs=[],
                timing=TimingInfo(start_time=start_time, end_time=datetime.now(timezone.utc)),
            )
            if (
                "validation error" in str(e).lower()
                or "concrete ModelRun" in str(e)
                or "concrete Postprocess" in str(e)
            ) and processor_input is not None:
                return result
            try:
                sidecar = PostprocessResultSidecar(
                    created_at=datetime.now(timezone.utc), run_id=self.run_id,
                    staging_dir=str(self.staging_dir), status="failed", success=False,
                    error=result.error, payload=result,
                )
                from rompy.core.result_persistence import persist_result
                return persist_result(result, sidecar, Path(self.staging_dir), primary_error=result.error)
            except Exception:
                return result

    def pipeline(self, pipeline_backend: str = "local", **kwargs) -> PipelineResult:
        """
        Run the complete model pipeline (generate, run, postprocess) using the specified pipeline backend.

        This method executes the entire model workflow from input generation through running
        the model to postprocessing outputs. It uses entry points to load and execute the
        appropriate pipeline backend from the rompy.pipeline entry point group.

        Built-in pipeline backends:
        - "local": Execute the complete pipeline locally using the existing ModelRun methods

        Args:
            pipeline_backend: Name of the pipeline backend to use (default: "local")
            **kwargs: Additional backend-specific parameters. Common parameters include:
                - backend_config: BackendConfig instance for the run stage (for local pipeline)
                - processor: ProcessorConfig instance for postprocessing (for local pipeline)
                - run_kwargs: Additional parameters for the run stage
                - process_kwargs: Additional parameters for postprocessing

        Returns:
            PipelineResult: Typed result object with success status, timing, stage tracking,
                and nested postprocess results.

                The result is a discriminated union:
                - PipelineSuccess: Contains stages_completed, nested postprocess_results, timing
                - PipelineFailure: Contains failed_stage, error, optional postprocess_results

        Raises:
            ValueError: If the specified pipeline backend is not available

        Examples:
            ::

                from rompy.backends import LocalConfig
                from rompy.postprocess.config import NoopPostprocessorConfig

                # Run complete pipeline
                result = model.pipeline(
                    pipeline_backend="local",
                    backend_config=LocalConfig(timeout=3600),
                    processor=NoopPostprocessorConfig()
                )

                # Type-safe result handling with discriminated union
                if result.success:
                    # Type narrowing: result is PipelineSuccess
                    print(f"Stages completed: {[s.value for s in result.stages_completed]}")
                    print(f"Total time: {result.timing.duration_seconds}s")

                    # Access nested postprocess results
                    pp_result = result.postprocess_results
                    if pp_result and pp_result.success:
                        print(f"Artifacts: {len(pp_result.artifacts)}")
                        for artifact in pp_result.artifacts:
                            print(f"  {artifact.type.value}: {artifact.path}")
                else:
                    # Type narrowing: result is PipelineFailure
                    print(f"Failed at stage: {result.failed_stage.value}")
                    print(f"Error: {result.error}")

                    # Check if postprocessing was attempted
                    if result.postprocess_results:
                        print("Postprocess also failed")

                # Serialize to dict for logging
                result_dict = result.model_dump()
        """
        # Get the requested pipeline backend class from entry points
        if pipeline_backend not in PIPELINE_BACKENDS:
            available = list(PIPELINE_BACKENDS.keys())
            raise ValueError(
                f"Unknown pipeline backend: {pipeline_backend}. "
                f"Available backends: {', '.join(available)}"
            )

        # Create an instance and execute the pipeline
        # Backend returns PipelineResult directly
        backend_class = PIPELINE_BACKENDS[pipeline_backend]
        backend_instance = backend_class()
        return backend_instance.execute(self, **kwargs)
