# Common Workflows

This section documents typical ocean modeling workflows and best practices using Rompy. For basic workflow concepts, please see the [Getting Started Guide](getting_started.md) and [Progressive Tutorials](progressive_tutorials.md).

## Common Workflow Patterns

### 1. Standard Model Simulation

The most common workflow for running a single model simulation:

1. Define spatial and temporal domain
2. Configure model-specific parameters
3. Set up data sources and boundary conditions
4. Validate configuration
5. Generate input files
6. Execute model run
7. Post-process results

### 2. Multi-Model Coupling

For complex simulations involving multiple models:

1. Configure individual model components
2. Set up data exchange between models
3. Define execution sequence or coupling mechanism
4. Execute coupled system
5. Validate consistency between models

### 3. Ensemble Simulations

Running multiple simulations with varying parameters:

1. Define base configuration
2. Set up parameter ranges for ensemble
3. Generate configurations for each ensemble member
4. Execute ensemble runs
5. Aggregate and analyze results

### 4. Operational Forecasting

For routine model runs such as weather forecasting:

1. Establish automated data acquisition pipeline
2. Configure model for operational constraints
3. Set up regular execution schedule
4. Implement monitoring and alerting
5. Archive and catalog results

### 5. Sensitivity Analysis

Systematically varying parameters to understand model behavior:

1. Define parameter space to explore
2. Generate configurations for each parameter combination
3. Execute all model runs
4. Analyze outputs for parameter sensitivity
5. Document findings and recommendations

## Best Practices

### Configuration Management
- Use version control for model configurations
- Maintain separate configurations for development, testing, and production
- Document configuration parameters and their impacts
- Perform validation checks before execution
- Use configuration factories for complex setups

### Execution Management
- Use appropriate backends for computational requirements
- Monitor resource usage during execution
- Implement proper error handling and recovery
- Log execution details for debugging and audit
- Plan for potential failures and implement retry mechanisms

### Data Management
- Use consistent data formats and conventions
- Implement data quality checks
- Maintain data lineage and provenance
- Plan for long-term data storage and access
- Consider data caching strategies for repeated access

### Model Validation
- Compare model output with observations when available
- Document model limitations and uncertainties
- Perform sensitivity analysis on key parameters
- Validate model physics for specific applications
- Establish validation metrics and acceptance criteria

## Integration Patterns

### Pattern 1: Data Pipeline Integration

Integrating Rompy with existing data pipelines:

```python
# Example: Integration with intake catalog for data acquisition
from rompy.core.source import SourceIntake

# Configure data source from catalog
data_source = SourceIntake(
    catalog="https://catalog.example.com/model_data.yml",
    entry="gfs_forecast",
)

# Use in model configuration
# model_config.data = data_source
```

### Pattern 2: Monitoring Integration

Integrating with monitoring systems:

```python
# Example: Logging model execution metrics
import logging
from rompy.model import ModelRun

# Setup logger
logger = logging.getLogger(__name__)

def run_monitored_model(config):
    model_run = ModelRun(**config)
    
    # Log execution start
    logger.info(f"Starting model run: {model_run.run_id}")
    
    try:
        # Execute model
        success = model_run.run(backend=config['backend'])
        
        # Log execution result
        if success:
            logger.info(f"Model run {model_run.run_id} completed successfully")
        else:
            logger.error(f"Model run {model_run.run_id} failed")
            
        return success
    except Exception as e:
        logger.error(f"Model run {model_run.run_id} encountered error: {e}")
        raise
```

### Pattern 3: Error Recovery

Implementing error recovery mechanisms:

```python
# Example: Retry mechanism for model execution
def run_with_retry(model_run, backend, max_retries=3):
    for attempt in range(max_retries):
        try:
            success = model_run.run(backend=backend)
            if success:
                return True
            else:
                logger.warning(f"Attempt {attempt + 1} failed")
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} encountered error: {e}")
        
        if attempt < max_retries - 1:
            logger.info(f"Retrying in 30 seconds... (attempt {attempt + 2})")
            time.sleep(30)
    
    return False
```

## Troubleshooting Common Issues

### Issue 1: Configuration Validation Failure

**Symptoms**: Model configuration fails with validation errors

**Solution**:
1. Check field names and value types against API documentation
2. Ensure required fields are provided
3. Verify value ranges and constraints
4. Use model's `model_dump()` method to inspect configuration

### Issue 2: Execution Backend Issues

**Symptoms**: Model fails to execute or hangs during execution

**Solutions**:
1. Check backend configuration parameters
2. Verify resource availability (CPU, memory, disk space)
3. Ensure model executable is accessible and has proper permissions
4. Check for network connectivity issues (for Docker/cloud backends)

### Issue 3: Data Access Problems

**Symptoms**: Model fails during data acquisition or processing

**Solutions**:
1. Verify data source URIs and access credentials
2. Check network connectivity to remote data sources
3. Validate data format and structure against expectations
4. Ensure sufficient local storage for data caching

## Performance Optimization

### Resource Management
- Right-size computational resources for your model requirements
- Consider using Docker for consistent environments
- Use parallel processing where possible for ensemble runs
- Optimize I/O operations when dealing with large datasets

### Configuration Optimization
- Pre-generate configurations to avoid runtime overhead
- Use appropriate grid resolutions for your application
- Optimize data access patterns and caching
- Profile model execution to identify bottlenecks

## Next Steps

- For specific model examples, see [Examples](examples.md)
- For model configuration details, see [Configuration Deep Dive](configuration_deep_dive.md)
- For backend options, see [Backends](backends.md)
- For API reference, see [API Reference](api.md)
- For model-specific guides, see [Models](models.md)