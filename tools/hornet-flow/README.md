# hornet-flow

A CLI tool for loading and processing hornet manifests from git repositories. It offers both a command line (CLI) and a programatic interfaces (API)

## Installation

```cmd
uv pip install "git+https://github.com/ITISFoundation/hornet-manifest-spec.git@main#subdirectory=tools/hornet-flow"
```

## CLI Usage

### Basic Commands 

```bash
# Show help
hornet-flow --help

# Show version
hornet-flow --version
```

### Workflow Operations

Run complete workflows to process hornet manifests:

```bash
# Using a metadata file
hornet-flow workflow run --metadata-file examples/portal-device-metadata.json --verbose

# Using inline repository parameters
hornet-flow workflow run --repo-url https://github.com/COSMIIC-Inc/Implantables-Electrodes --commit main --verbose

# Using an already-cloned repository
hornet-flow workflow run --repo-path /path/to/local/repo --verbose

# Using a specific plugin
hornet-flow workflow run --repo-url https://github.com/CARSSCenter/Sub-mm-Parylene-Cuff-Electrode --plugin osparc --verbose

# With component filtering
hornet-flow workflow run --repo-path /path/to/repo --type-filter assembly --verbose
hornet-flow workflow run --repo-path /path/to/repo --name-filter electrode --verbose

# Fail fast mode (stop on first error)
hornet-flow workflow run --metadata-file examples/metadata.json --fail-fast

# Watch for metadata.json files and auto-process them
hornet-flow workflow watch --inputs-dir /path/to/inputs --work-dir /path/to/work --verbose

# Watch mode with environment variables
export INPUTS_DIR=/path/to/inputs
export WORK_DIR=/path/to/work
hornet-flow workflow watch --verbose

# Single file mode (exit after processing one file)
hornet-flow workflow watch --inputs-dir /path/to/inputs --work-dir /path/to/work --once
```

### Repository Operations

Clone repositories and manage git operations:

```bash
# Clone repository to default temp directory
hornet-flow repo clone --repo-url https://github.com/COSMIIC-Inc/Implantables-Electrodes

# Clone to specific destination
hornet-flow repo clone --repo-url https://github.com/COSMIIC-Inc/Implantables-Electrodes --dest /tmp/my-repo

# Clone specific commit
hornet-flow repo clone --repo-url https://github.com/COSMIIC-Inc/Implantables-Electrodes --commit 095a255 --dest /tmp/my-repo
```

### Manifest Operations

Validate and display manifest contents:

```bash
# Validate all manifests in repository
hornet-flow manifest validate --repo-path /path/to/repo

# Show all manifests (default)
hornet-flow manifest show --repo-path /path/to/repo

# Show only CAD manifest
hornet-flow manifest show --repo-path /path/to/repo --type cad

# Show only SIM manifest
hornet-flow manifest show --repo-path /path/to/repo --type sim

# Show both manifests explicitly
hornet-flow manifest show --repo-path /path/to/repo --type both
```

### CAD Operations

Load and process CAD files:

```bash
# Load CAD files from manifest
hornet-flow cad load --repo-path /path/to/repo --verbose
```

### Plugin System

Hornet-flow supports plugins for processing manifest components:

```bash
# List available plugins
hornet-flow workflow run --help  # Shows plugin options

# Use specific plugin
hornet-flow workflow run --repo-path /path/to/repo --plugin debug --verbose
hornet-flow workflow run --repo-path /path/to/repo --plugin osparc --verbose

# Component filtering with plugins
hornet-flow workflow run --repo-path /path/to/repo --plugin debug --type-filter assembly
hornet-flow workflow run --repo-path /path/to/repo --plugin debug --name-filter electrode
```

**Available Plugins:**

- `debug`: Simple logging plugin for testing and debugging
- `osparc`: Integration with OSparc for CAD file loading

### Global Options

All commands support these logging options:

```bash
# Verbose logging (debug level)
hornet-flow <command> --verbose

# Quiet mode (errors only)
hornet-flow <command> --quiet

# Regular logging (info level) - default
hornet-flow <command>
```

### Examples

#### Complete Workflow

Process manifests from a metadata file with cleanup:

```bash
hornet-flow workflow run \
  --metadata-file examples/portal-device-metadata.json \
  --work-dir /tmp/hornet-flow \
  --cleanup \
  --verbose
```

#### Automated File Watching

Watch for incoming metadata files and process them automatically:

```bash
# Basic watching with environment variables
export INPUTS_DIR=/shared/inputs
export WORK_DIR=/shared/work
hornet-flow workflow watch --verbose

# Watch with explicit paths
hornet-flow workflow watch \
  --inputs-dir /shared/inputs \
  --work-dir /shared/work \
  --verbose

# Single file mode (Docker container scenario)
hornet-flow workflow watch \
  --inputs-dir /shared/inputs \
  --work-dir /shared/work \
  --once \
  --verbose

# With plugin and filtering options
hornet-flow workflow watch \
  --inputs-dir /shared/inputs \
  --work-dir /shared/work \
  --plugin osparc \
  --type-filter assembly \
  --fail-fast \
  --stability-seconds 3.0 \
  --verbose
```

**Docker Container Usage:**
```bash
# Run in a container watching for files
docker run -v /host/inputs:/shared/inputs \
           -v /host/work:/shared/work \
           -e INPUTS_DIR=/shared/inputs \
           -e WORK_DIR=/shared/work \
           my-hornet-flow:latest \
           hornet-flow workflow watch --once --verbose
```

#### Step-by-Step Workflow

1. **Clone a repository:**
```bash
hornet-flow repo clone \
  --repo-url https://github.com/CARSSCenter/Sub-mm-Parylene-Cuff-Electrode \
  --dest /tmp/electrodes \
  --verbose
```

2. **Validate manifests:**
```bash
hornet-flow manifest validate --repo-path /tmp/electrodes --verbose
```

3. **Show manifest contents:**
```bash
# Show CAD manifest only
hornet-flow manifest show --repo-path /tmp/electrodes --type cad

# Show SIM manifest only
hornet-flow manifest show --repo-path /tmp/electrodes --type sim

# Show both manifests
hornet-flow manifest show --repo-path /tmp/electrodes --type both
```

4. **Load CAD files:**
```bash
hornet-flow cad load --repo-path /tmp/electrodes --verbose
```

#### Using Different Input Methods

**With metadata file:**
```bash
hornet-flow workflow run \
  --metadata-file examples/portal-device-metadata.json \
  --verbose
```

**With inline repository parameters:**
```bash
hornet-flow workflow run \
  --repo-url https://github.com/CARSSCenter/Sub-mm-Parylene-Cuff-Electrode \
  --commit abc123 \
  --verbose
```

**With existing local repository:**
```bash
hornet-flow workflow run \
  --repo-path /path/to/existing/repo \
  --verbose
```

#### Error Handling

**Fail fast mode (stop on first error):**
```bash
hornet-flow workflow run \
  --metadata-file examples/metadata.json \
  --fail-fast \
  --verbose
```

**Quiet mode (only show errors):**
```bash
hornet-flow manifest validate \
  --repo-path /tmp/electrodes \
  --quiet
```

## Programmatic API Usage

In addition to the CLI, hornet-flow provides a clean programmatic API for integration into other applications:

### Class-based API (Recommended)

```python
from hornet_flow.api import HornetFlowAPI

# Create API instance
api = HornetFlowAPI()

# Workflow operations
success_count, total_count = api.workflow.run(
    repo_url="https://github.com/COSMIIC-Inc/Implantables-Electrodes",
    plugin="osparc",
    fail_fast=True
)

# Repository operations
repo_path = api.repo.clone(
    repo_url="https://github.com/CARSSCenter/Sub-mm-Parylene-Cuff-Electrode",
    dest="/tmp/my-repo",
    commit="main"
)

# Manifest operations
cad_valid, sim_valid = api.manifest.validate("/path/to/repo")
manifest_data = api.manifest.show("/path/to/repo", manifest_type="cad")

# CAD operations
success_count, total_count = api.cad.load(
    repo_path="/path/to/repo",
    plugin="debug",
    type_filter="assembly"
)
```

### Function-based API (Backward Compatibility)

```python
from hornet_flow.api import (
    run_workflow_api,
    clone_repository_api,
    validate_manifests_api,
    show_manifest_api,
    load_cad_api
)

# Same functionality as class-based API
success_count, total_count = run_workflow_api(
    repo_url="https://github.com/COSMIIC-Inc/Implantables-Electrodes",
    plugin="osparc"
)

repo_path = clone_repository_api(
    repo_url="https://github.com/example/repo",
    dest="/tmp/repo"
)
```

### API Examples

**Complete workflow with error handling:**
```python
from hornet_flow.api import HornetFlowAPI
from hornet_flow.exceptions import ApiProcessingError, ApiValidationError

api = HornetFlowAPI()

try:
    # Clone repository
    repo_path = api.repo.clone(
        repo_url="https://github.com/COSMIIC-Inc/Implantables-Electrodes",
        dest="/tmp/electrodes"
    )
    
    # Validate manifests
    cad_valid, sim_valid = api.manifest.validate(str(repo_path))
    print(f"CAD valid: {cad_valid}, SIM valid: {sim_valid}")
    
    # Run workflow
    success_count, total_count = api.workflow.run(
        repo_path=str(repo_path),
        plugin="osparc",
        fail_fast=True
    )
    
    print(f"Processed {success_count}/{total_count} components")
    
except ApiValidationError as e:
    print(f"Validation failed: {e}")
except ApiProcessingError as e:
    print(f"Processing failed: {e}")
```

**Batch processing multiple repositories:**
```python
from hornet_flow.api import HornetFlowAPI

api = HornetFlowAPI()

repositories = [
    "https://github.com/COSMIIC-Inc/Implantables-Electrodes",
    "https://github.com/CARSSCenter/Sub-mm-Parylene-Cuff-Electrode"
]

for repo_url in repositories:
    try:
        # Process each repository
        success_count, total_count = api.workflow.run(
            repo_url=repo_url,
            plugin="debug",
            work_dir="/tmp/batch-processing"
        )
        print(f"{repo_url}: {success_count}/{total_count} components processed")
    except Exception as e:
        print(f"Failed to process {repo_url}: {e}")
```

**Working with existing repositories:**
```python
from hornet_flow.api import HornetFlowAPI

api = HornetFlowAPI()

# Show manifest contents
manifest_data = api.manifest.show("/path/to/local/repo", manifest_type="both")

if "cad" in manifest_data:
    print("CAD Manifest:")
    print(manifest_data["cad"])

if "sim" in manifest_data:
    print("SIM Manifest:")
    print(manifest_data["sim"])

# Load CAD files with filtering
success_count, total_count = api.cad.load(
    repo_path="/path/to/local/repo",
    plugin="osparc",
    type_filter="assembly",
    name_filter="electrode"
)
```


## Development

See the Makefile for development commands:

```bash
make help           # Show available targets
make install-all    # Install all dependencies
make test          # Run tests
make lint          # Run linting
```




