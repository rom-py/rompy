"""
Docker backend for running models.

This module provides a Docker-based execution backend for rompy models.
"""

import hashlib
import json
import logging
import pathlib
import subprocess
import time
from typing import TYPE_CHECKING, Dict, List, Optional

import docker
from docker.errors import APIError, BuildError, ContainerError, ImageNotFound

if TYPE_CHECKING:
    from rompy.backends import DockerConfig

logger = logging.getLogger(__name__)


class DockerRunBackend:
    """Execute models inside Docker containers.

    This backend builds Docker images if needed and runs models
    inside containers with appropriate volume mounts.
    """

    def run(
        self, model_run, config: "DockerConfig", workspace_dir: Optional[str] = None
    ) -> bool:
        """Run the model inside a Docker container.

        Args:
            model_run: The ModelRun instance to execute
            config: DockerConfig instance with execution parameters
            workspace_dir: Path to the generated workspace directory (if None, will generate)

        Returns:
            True if execution was successful, False otherwise
        """
        # Use config parameters
        exec_image = config.image
        exec_dockerfile = str(config.dockerfile) if config.dockerfile else None
        exec_executable = config.executable
        exec_mpiexec = config.mpiexec
        exec_cpu = config.cpu
        exec_build_args = config.build_args
        exec_volumes = config.volumes
        exec_env_vars = config.env_vars

        logger.debug(f"Using DockerConfig: image={exec_image}, cpu={exec_cpu}")

        # Use provided workspace or generate if not provided (for backwards compatibility)
        if workspace_dir is None:
            logger.warning(
                "No workspace_dir provided, generating files (this may cause double generation in pipeline)"
            )
            workspace_dir = model_run.generate()
        else:
            logger.info(f"Using provided workspace directory: {workspace_dir}")

        try:
            # Build or use a Docker image
            image_name = self._prepare_image(
                exec_image,
                exec_dockerfile,
                str(config.build_context) if config.build_context else None,
                exec_build_args,
            )
            if not image_name:
                return False

            # Set up the run command
            run_command = self._get_run_command(exec_executable, exec_mpiexec, exec_cpu)

            # Set up volume mounts
            volume_mounts = self._prepare_volumes(
                model_run, exec_volumes, workspace_dir
            )

            # Run the Docker container
            success = self._run_container(
                image_name=image_name,
                run_command=run_command,
                volume_mounts=volume_mounts,
                env_vars=exec_env_vars,
            )

            return success
        except Exception as e:
            logger.exception(f"Failed to run model in Docker: {e}")
            return False

    def _prepare_image(
        self,
        image: Optional[str],
        dockerfile: Optional[str],
        build_context: Optional[str] = None,
        build_args: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """Prepare the Docker image to use.

        This will either use a pre-built image or build one from a Dockerfile.

        Args:
            image: Docker image to use
            dockerfile: Path to Dockerfile relative to build context
            build_context: Docker build context directory
            build_args: Arguments to pass to docker build

        Returns:
            Image name to use, or None if preparation failed
        """
        # If image is provided, use it directly
        if image:
            logger.info(f"Using provided Docker image: {image}")
            return image

        # If Dockerfile is provided, build the image
        if dockerfile:
            # Determine build context
            if build_context:
                context_path = pathlib.Path(build_context)
                # dockerfile is relative to build_context
                dockerfile_path = context_path / dockerfile
            else:
                # dockerfile is absolute path, use its parent as context
                dockerfile_path = pathlib.Path(dockerfile)
                context_path = dockerfile_path.parent

            # Generate deterministic image name based on content
            image_name = self._generate_image_name(
                dockerfile_path, context_path, build_args
            )

            # Check if image already exists
            if self._image_exists(image_name):
                logger.info(f"Using existing Docker image: {image_name}")
                return image_name

            # Build the Docker image using docker-py
            logger.info(
                f"Building Docker image {image_name} from {dockerfile} (context: {context_path})"
            )

            try:
                client = docker.from_env()
                image_obj, build_logs = client.images.build(
                    path=str(context_path),
                    dockerfile=str(dockerfile_path.relative_to(context_path)),
                    tag=image_name,
                    buildargs=build_args or {},
                    rm=True,
                )

                # Log build output
                for line in build_logs:
                    if "stream" in line:
                        logger.debug(line["stream"].strip())

                logger.info(f"Successfully built Docker image: {image_name}")
                return image_name
            except BuildError as e:
                logger.error(f"Docker build failed: {e.msg}")
                for line in e.build_log:
                    if "error" in line:
                        logger.error(f"Build error: {line['error']}")
                return None
            except APIError as e:
                logger.error(f"Docker API error during build: {e}")
                return None

        # If neither is provided, use a default image
        logger.warning("No image or Dockerfile provided, using default rompy image")
        return "rompy/rompy:latest"

    def _get_run_command(self, executable: str, mpiexec: str, cpu: int) -> str:
        """Create the run command to execute inside the container.

        Args:
            executable: Path to the executable
            mpiexec: MPI execution command
            cpu: Number of CPU cores

        Returns:
            Command string to execute
        """
        # Add diagnostic commands to list directory contents and verify input file
        diagnostics = (
            "cd /app/run_id && "
            "echo 'Directory contents:' && "
            "ls -la && "
            "echo 'Executing model...'"
        )

        if mpiexec:
            # Add --allow-run-as-root flag for MPI inside Docker containers
            return (
                f"{diagnostics} && {mpiexec} --allow-run-as-root -n {cpu} {executable}"
            )
        return f"{diagnostics} && {executable}"

    def _prepare_volumes(
        self,
        model_run,
        additional_volumes: Optional[List[str]] = None,
        workspace_dir: Optional[str] = None,
    ) -> List[str]:
        """Prepare volume mounts for the Docker container.

        Args:
            model_run: The ModelRun instance
            additional_volumes: Additional volumes to mount
            workspace_dir: Path to the workspace directory to mount

        Returns:
            List of volume mount specifications
        """
        # Mount the workspace directory (generated files) into the container
        # Add :Z for SELinux contexts and proper permissions
        if workspace_dir:
            workspace_path = pathlib.Path(workspace_dir)
            volumes = [f"{workspace_path.absolute()}:/app/run_id:Z"]
        else:
            # Fallback to run directory for backwards compatibility
            run_dir = model_run.output_dir / model_run.run_id
            volumes = [f"{run_dir.absolute()}:/app/run_id:Z"]

        # Add any additional volumes
        if additional_volumes:
            volumes.extend(additional_volumes)

        return volumes

    def _run_container(
        self,
        image_name: str,
        run_command: str,
        volume_mounts: List[str],
        env_vars: Dict[str, str],
    ) -> bool:
        """Run the Docker container with the given configuration.

        Args:
            image_name: Docker image to use
            run_command: Command to run inside the container
            volume_mounts: Volume mounts to set up
            env_vars: Environment variables to pass to the container

        Returns:
            True if execution was successful, False otherwise
        """
        try:
            client = docker.from_env()

            # Convert volume mounts to docker-py format
            volumes = {}
            for volume in volume_mounts:
                parts = volume.split(":")
                if len(parts) >= 2:
                    host_path, container_path = parts[0], parts[1]
                    mode = "rw"  # default mode
                    if len(parts) > 2:
                        mode = parts[2] if parts[2] in ["ro", "rw", "Z"] else "rw"
                    volumes[host_path] = {"bind": container_path, "mode": mode}

            # Prepare container configuration
            container_config = {
                "image": image_name,
                "command": ["bash", "-c", run_command],
                "environment": env_vars,
                "volumes": volumes,
                "user": "root",
                "remove": True,  # Remove container after run
                "stdout": True,
                "stderr": True,
            }

            logger.info(f"Running Docker container with image: {image_name}")
            logger.debug(f"Command: {run_command}")
            logger.debug(f"Volumes: {volumes}")
            logger.debug(f"Environment: {env_vars}")

            # Run the container
            container = client.containers.run(**container_config)

            # Log output
            if container:
                logger.info("Model run completed successfully")
                return True
            else:
                logger.error("Model run failed - no output from container")
                return False

        except ContainerError as e:
            logger.error(f"Container error: {e}")
            if e.stderr:
                logger.error(f"Container stderr: {e.stderr}")
            return False
        except ImageNotFound:
            logger.error(f"Docker image not found: {image_name}")
            return False
        except APIError as e:
            logger.error(f"Docker API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Docker run error: {str(e)}")
            return False

    def _generate_image_name(
        self,
        dockerfile_path: pathlib.Path,
        context_path: pathlib.Path,
        build_args: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate a deterministic image name based on Dockerfile content and build args.

        Args:
            dockerfile_path: Path to the Dockerfile
            context_path: Path to the build context
            build_args: Build arguments that affect the image

        Returns:
            Deterministic image name
        """
        # Create a hash based on:
        # 1. Dockerfile content
        # 2. Build arguments
        # 3. Build context path (affects COPY/ADD operations)
        hasher = hashlib.sha256()

        # Hash Dockerfile content
        try:
            with open(dockerfile_path, "rb") as f:
                hasher.update(f.read())
        except Exception as e:
            logger.warning(f"Could not read Dockerfile for hashing: {e}")
            # Fallback to timestamp-based naming
            return f"rompy-{int(time.time())}"

        # Hash build arguments (sorted for consistency)
        if build_args:
            build_args_str = json.dumps(build_args, sort_keys=True)
            hasher.update(build_args_str.encode())

        # Hash context path (affects relative paths in Dockerfile)
        hasher.update(str(context_path.absolute()).encode())

        # Generate short hash for image name
        image_hash = hasher.hexdigest()[:12]
        return f"rompy-{image_hash}"

    def _image_exists(self, image_name: str) -> bool:
        """Check if a Docker image already exists locally.

        Args:
            image_name: Name of the image to check

        Returns:
            True if image exists, False otherwise
        """
        try:
            client = docker.from_env()
            client.images.get(image_name)
            logger.debug(f"Image {image_name} already exists")
            return True
        except ImageNotFound:
            logger.debug(f"Image {image_name} does not exist")
            return False
        except APIError as e:
            logger.error(f"Error checking for image {image_name}: {e}")
            return False
