class SlurmConfig(BaseBackendConfig):
    """Configuration for SLURM cluster execution."""

    queue: Optional[str] = Field(
        None, 
        description="SLURM partition name (equivalent to queue)"
    )
    nodes: int = Field(
        1, 
        ge=1, 
        le=100, 
        description="Number of nodes to allocate"
    )
    ntasks: int = Field(
        1, 
        ge=1, 
        description="Number of tasks (processes) to run"
    )
    cpus_per_task: int = Field(
        1, 
        ge=1, 
        le=128, 
        description="Number of CPU cores per task"
    )
    time_limit: str = Field(
        "1:00:00", 
        description="Time limit in format HH:MM:SS"
    )
    account: Optional[str] = Field(
        None, 
        description="Account for billing/resource tracking"
    )
    qos: Optional[str] = Field(
        None, 
        description="Quality of Service for the job"
    )
    reservation: Optional[str] = Field(
        None, 
        description="Reservation name to run job under"
    )
    output_file: Optional[str] = Field(
        None, 
        description="Output file path for job output"
    )
    error_file: Optional[str] = Field(
        None, 
        description="Error file path for job errors"
    )
    job_name: Optional[str] = Field(
        None, 
        description="Name for the SLURM job"
    )
    mail_type: Optional[str] = Field(
        None,
        description="Type of mail to send (BEGIN, END, FAIL, ALL, etc.)"
    )
    mail_user: Optional[str] = Field(
        None,
        description="Email address for notifications"
    )
    additional_options: List[str] = Field(
        default_factory=list,
        description="Additional SLURM options (e.g., '--gres=gpu:1')"
    )

    @field_validator('time_limit')
    @classmethod
    def validate_time_limit(cls, v):
        """Validate time limit format (HH:MM:SS)."""
        import re
        if not re.match(r'^\d{1,4}:\d{2}:\d{2}$', v):
            raise ValueError("Time limit must be in format HH:MM:SS")
        return v

    def get_backend_class(self):
        """Return the SlurmRunBackend class."""
        from rompy.run.slurm import SlurmRunBackend
        return SlurmRunBackend

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "queue": "general",
                    "nodes": 1,
                    "ntasks": 1,
                    "cpus_per_task": 4,
                    "time_limit": "02:00:00",
                    "account": "myproject",
                    "timeout": 7200,
                },
                {
                    "queue": "gpu",
                    "nodes": 2,
                    "ntasks": 8,
                    "cpus_per_task": 2,
                    "time_limit": "24:00:00",
                    "reservation": "special_reservation",
                    "additional_options": ["--gres=gpu:v100:2"],
                },
            ]
        }
    )