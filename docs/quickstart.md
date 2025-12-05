# Quickstart

## Installation

### Install from PyPI

```bash
pip install rompy
```

### Install from source code

```bash
git clone git@github.com:rom-py/rompy.git
cd rompy
pip install -e .
```

## Usage

### Simple example

```python
from rompy import ModelRun

# Initiate a model run
run = ModelRun()

# Execute the model run
run()
```