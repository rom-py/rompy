"""
Docker backend for running models.

This module provides a Docker-based execution backend for rompy models.
"""

import hashlib
import json
import logging
import os
import pathlib
import subprocess
import time
from typing import TYPE_CHECKING, Dict, List, Optional

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

            # Build arguments
            build_args_list = []
            if build_args:
                for key, value in build_args.items():
                    build_args_list.extend(["--build-arg", f"{key}={value}"])

            # Build the Docker image
            logger.info(
                f"Building Docker image {image_name} from {dockerfile} (context: {context_path})"
            )
            build_cmd = [
                "docker",
                "build",
                "-t",
                image_name,
                "-f",
                str(dockerfile_path),  # Use full path for -f flag
                *build_args_list,
                str(context_path),
            ]

            try:
                result = subprocess.run(
                    build_cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                logger.debug(f"Docker build output: {result.stdout}")
                return image_name
            except subprocess.CalledProcessError as e:
                logger.error(f"Docker build failed: {e.stderr}")
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
        # Set up the Docker command
        docker_cmd = [
            "docker",
            "run",
            "--rm",  # Remove container after run
            "--user",
            "root",  # Run as root to avoid permission issues
        ]

        # Add environment variables
        for key, value in env_vars.items():
            docker_cmd.extend(["-e", f"{key}={value}"])

        # Add volume mounts
        for volume in volume_mounts:
            docker_cmd.extend(["-v", volume])

        # Add the image name and command
        docker_cmd.append(image_name)

        # Add bash and -c as separate arguments
        docker_cmd.append("bash")
        docker_cmd.append("-c")

        # Add the run command as a separate argument
        docker_cmd.append(run_command)

        try:
            logger.info(f"Executing: {' '.join(docker_cmd)}")
            # Don't use check=True, so we can see the output even if it fails
            result = subprocess.run(
                docker_cmd,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Always log the output regardless of success/failure
            if result.stdout:
                logger.info(f"Docker stdout: \n{result.stdout}")
            if result.stderr:
                logger.warning(f"Docker stderr: \n{result.stderr}")

            # Check return code manually
            if result.returncode == 0:
                logger.info(f"Model run completed successfully with exit code 0")
                return True
            else:
                logger.error(f"Model run failed with exit code {result.returncode}")
                logger.error(f"Command: {' '.join(docker_cmd)}")
                return False

        except Exception as e:
            logger.error(f"Docker run error: {str(e)}")
            logger.error(f"Command: {' '.join(docker_cmd)}")
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
            result = subprocess.run(
                ["docker", "image", "inspect", image_name],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.debug(f"Image {image_name} already exists")
            return True
        except subprocess.CalledProcessError:
            logger.debug(f"Image {image_name} does not exist")
            return False
