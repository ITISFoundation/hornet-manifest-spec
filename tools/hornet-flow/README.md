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

### Event System

The API supports an event system that allows you to hook into specific workflow stages:

```python
from hornet_flow.api import HornetFlowAPI, EventDispatcher, WorkflowEvent

# Create event dispatcher
dispatcher = EventDispatcher()

# Register callback for before manifest processing
def check_external_readiness(**kwargs):
    repo_path = kwargs['repo_path']
    print(f"Checking external system readiness for repo: {repo_path}")

    # Your custom logic here - e.g., check if external service is ready
    # You can access: repo_path, cad_manifest, sim_manifest, release
    cad_manifest = kwargs.get('cad_manifest')
    sim_manifest = kwargs.get('sim_manifest')
    release = kwargs.get('release')

    print(f"Found CAD manifest: {cad_manifest}")
    print(f"Found SIM manifest: {sim_manifest}")

    # Raise an exception to stop the workflow if external system not ready
    # raise RuntimeError("External system not ready")

# Register the callback
dispatcher.register(WorkflowEvent.MANIFEST_READY, check_external_readiness)

# Create API instance
api = HornetFlowAPI()

# Run workflow with event dispatcher
success_count, total_count = api.workflow.run(
    repo_url="https://github.com/COSMIIC-Inc/Implantables-Electrodes",
    plugin="osparc",
    event_dispatcher=dispatcher
)
```

**Multiple Event Handlers:**
```python
from hornet_flow.api import HornetFlowAPI, EventDispatcher, WorkflowEvent
import requests

dispatcher = EventDispatcher()

# Handler 1: Check external service availability
def check_service_health(**kwargs):
    try:
        response = requests.get("http://external-service/health", timeout=5)
        if response.status_code != 200:
            raise RuntimeError("External service is not healthy")
        print("✓ External service is ready")
    except requests.RequestException as e:
        raise RuntimeError(f"Cannot reach external service: {e}")

# Handler 2: Log workflow progress
def log_workflow_progress(**kwargs):
    repo_path = kwargs['repo_path']
    print(f"📋 About to process manifests in: {repo_path}")

# Handler 3: Send notification
def send_notification(**kwargs):
    repo_path = kwargs['repo_path']
    # Send to monitoring system, Slack, etc.
    print(f"🔔 Starting manifest processing for {repo_path}")

# Register all handlers
dispatcher.register(WorkflowEvent.MANIFEST_READY, check_service_health)
dispatcher.register(WorkflowEvent.MANIFEST_READY, log_workflow_progress)
dispatcher.register(WorkflowEvent.MANIFEST_READY, send_notification)

# Run workflow
api = HornetFlowAPI()
success_count, total_count = api.workflow.run(
    repo_url="https://github.com/COSMIIC-Inc/Implantables-Electrodes",
    event_dispatcher=dispatcher
)
```

**Conditional Workflow Control:**
```python
from hornet_flow.api import HornetFlowAPI, EventDispatcher, WorkflowEvent
import os
import time

dispatcher = EventDispatcher()

def wait_for_external_system(**kwargs):
    """Wait for external system to be ready before processing."""
    max_attempts = 10
    attempt = 0

    while attempt < max_attempts:
        # Check if external system is ready (e.g., file exists, service responds)
        if os.path.exists("/tmp/external_system_ready.flag"):
            print("✓ External system is ready, proceeding with manifest processing")
            return

        attempt += 1
        print(f"⏳ Waiting for external system... (attempt {attempt}/{max_attempts})")
        time.sleep(2)

    # If we get here, external system is not ready
    raise RuntimeError("External system not ready after maximum wait time")

dispatcher.register(WorkflowEvent.MANIFEST_READY, wait_for_external_system)

api = HornetFlowAPI()
success_count, total_count = api.workflow.run(
    repo_path="/path/to/repo",
    event_dispatcher=dispatcher
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

**Automated file watching:**
```python
from hornet_flow.api import HornetFlowAPI
from hornet_flow.exceptions import ApiFileNotFoundError, ApiInputValueError
import os
from pathlib import Path

api = HornetFlowAPI()

# Get directories from environment or use defaults
inputs_dir = os.getenv("INPUTS_DIR", "/shared/inputs")
work_dir = os.getenv("WORK_DIR", "/shared/work")

try:
    # Watch for metadata.json files continuously
    api.workflow.watch(
        inputs_dir=inputs_dir,
        work_dir=str(Path(work_dir) / "hornet-flows"),
        once=False,  # Continuous watching
        plugin="osparc",
        type_filter="assembly",
        fail_fast=False,
        stability_seconds=3.0
    )

except KeyboardInterrupt:
    print("Watcher stopped by user")
except ApiFileNotFoundError as e:
    print(f"Directory not found: {e}")
except ApiInputValueError as e:
    print(f"Invalid input: {e}")
except Exception as e:
    print(f"Watcher failed: {e}")
```

**Single-time processing mode**

```python
from hornet_flow.api import HornetFlowAPI
import os

api = HornetFlowAPI()

# Process one file and exit (useful for Docker containers)
try:
    api.workflow.watch(
        inputs_dir=os.getenv("INPUTS_DIR", "/shared/inputs"),
        work_dir=os.getenv("WORK_DIR", "/shared/work"),
        once=True,  # Exit after processing one file
        plugin="osparc",
        fail_fast=True,
        stability_seconds=2.0
    )
    print("Successfully processed one metadata file")

except Exception as e:
    print(f"Processing failed: {e}")
    exit(1)
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


## Development workflow

```bash
make help           # Show available targets
make install-all    # Install all dependencies
make lint           # Run linting
make tests          # Run tests
```
