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

In addition to the CLI, hornet-flow provides a clean programmatic **async API** for integration into other applications.

> **Note:** The API is fully async using Python's `asyncio`. All API methods must be awaited and run within an async context.

### Class-based Async API (Recommended)

```python
import asyncio
from hornet_flow.api import HornetFlowAPI

async def main():
    # Create API instance
    api = HornetFlowAPI()

    # Workflow operations
    success_count, total_count = await api.workflow.run(
        repo_url="https://github.com/COSMIIC-Inc/Implantables-Electrodes",
        plugin="osparc",
        fail_fast=True
    )

    # Repository operations
    repo_path = await api.repo.clone(
        repo_url="https://github.com/CARSSCenter/Sub-mm-Parylene-Cuff-Electrode",
        dest="/tmp/my-repo",
        commit="main"
    )

    # Manifest operations
    cad_valid, sim_valid = await api.manifest.validate("/path/to/repo")
    manifest_data = await api.manifest.show("/path/to/repo", manifest_type="cad")

    # CAD operations
    success_count, total_count = await api.cad.load(
        repo_path="/path/to/repo",
        plugin="debug",
        type_filter="assembly"
    )

# Run the async function
asyncio.run(main())
```

### Async Event System

The API supports an **async event system** that allows you to hook into specific workflow stages. All event callbacks must be async functions:

```python
import asyncio
from hornet_flow.api import HornetFlowAPI, AsyncEventDispatcher, WorkflowEvent

async def main():
    # Create async event dispatcher
    dispatcher = AsyncEventDispatcher()

    # Register async callback for before manifest processing
    async def check_external_readiness(**kwargs):
        repo_path = kwargs['repo_path']
        print(f"Checking external system readiness for repo: {repo_path}")

        # Your custom async logic here - e.g., check if external service is ready
        # You can access: repo_path, cad_manifest, sim_manifest, release
        cad_manifest = kwargs.get('cad_manifest')
        sim_manifest = kwargs.get('sim_manifest')
        release = kwargs.get('release')

        print(f"Found CAD manifest: {cad_manifest}")
        print(f"Found SIM manifest: {sim_manifest}")

        # Raise an exception to stop the workflow if external system not ready
        # raise RuntimeError("External system not ready")

    # Register the callback
    dispatcher.register(WorkflowEvent.MANIFESTS_READY, check_external_readiness)

    # Create API instance
    api = HornetFlowAPI()

    # Run workflow with event dispatcher
    success_count, total_count = await api.workflow.run(
        repo_url="https://github.com/COSMIIC-Inc/Implantables-Electrodes",
        plugin="osparc",
        event_dispatcher=dispatcher
    )

asyncio.run(main())
```

**Multiple Async Event Handlers:**
```python
import asyncio
from hornet_flow.api import HornetFlowAPI, AsyncEventDispatcher, WorkflowEvent
import httpx  # Async HTTP client

async def main():
    dispatcher = AsyncEventDispatcher()

    # Handler 1: Check external service availability (async HTTP)
    async def check_service_health(**kwargs):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://external-service/health", timeout=5.0)
                if response.status_code != 200:
                    raise RuntimeError("External service is not healthy")
                print("✓ External service is ready")
            except httpx.RequestError as e:
                raise RuntimeError(f"Cannot reach external service: {e}")

    # Handler 2: Log workflow progress (with async I/O)
    async def log_workflow_progress(**kwargs):
        repo_path = kwargs['repo_path']
        # Could write to async log file, database, etc.
        print(f"📋 About to process manifests in: {repo_path}")

    # Handler 3: Send async notification
    async def send_notification(**kwargs):
        repo_path = kwargs['repo_path']
        # Send to monitoring system, Slack, etc. using async HTTP
        print(f"🔔 Starting manifest processing for {repo_path}")

    # Register all handlers
    dispatcher.register(WorkflowEvent.MANIFESTS_READY, check_service_health)
    dispatcher.register(WorkflowEvent.MANIFESTS_READY, log_workflow_progress)
    dispatcher.register(WorkflowEvent.MANIFESTS_READY, send_notification)

    # Run workflow
    api = HornetFlowAPI()
    success_count, total_count = await api.workflow.run(
        repo_url="https://github.com/COSMIIC-Inc/Implantables-Electrodes",
        event_dispatcher=dispatcher
    )

asyncio.run(main())
```

**Conditional Workflow Control with Async:**
```python
import asyncio
from hornet_flow.api import HornetFlowAPI, AsyncEventDispatcher, WorkflowEvent
from pathlib import Path

async def main():
    dispatcher = AsyncEventDispatcher()

    async def wait_for_external_system(**kwargs):
        """Wait for external system to be ready before processing."""
        max_attempts = 10
        attempt = 0

        while attempt < max_attempts:
            # Check if external system is ready (e.g., file exists, service responds)
            if Path("/tmp/external_system_ready.flag").exists():
                print("✓ External system is ready, proceeding with manifest processing")
                return

            attempt += 1
            print(f"⏳ Waiting for external system... (attempt {attempt}/{max_attempts})")
            await asyncio.sleep(2)  # Non-blocking async sleep

        # If we get here, external system is not ready
        raise RuntimeError("External system not ready after maximum wait time")

    dispatcher.register(WorkflowEvent.MANIFESTS_READY, wait_for_external_system)

    api = HornetFlowAPI()
    success_count, total_count = await api.workflow.run(
        repo_path="/path/to/repo",
        event_dispatcher=dispatcher
    )

asyncio.run(main())
```

### API Examples

**Complete workflow with error handling:**
```python
import asyncio
from hornet_flow.api import HornetFlowAPI
from hornet_flow.exceptions import ApiProcessingError, ApiValidationError

async def main():
    api = HornetFlowAPI()

    try:
        # Clone repository
        repo_path = await api.repo.clone(
            repo_url="https://github.com/COSMIIC-Inc/Implantables-Electrodes",
            dest="/tmp/electrodes"
        )

        # Validate manifests
        cad_valid, sim_valid = await api.manifest.validate(str(repo_path))
        print(f"CAD valid: {cad_valid}, SIM valid: {sim_valid}")

        # Run workflow
        success_count, total_count = await api.workflow.run(
            repo_path=str(repo_path),
            plugin="osparc",
            fail_fast=True
        )

        print(f"Processed {success_count}/{total_count} components")

    except ApiValidationError as e:
        print(f"Validation failed: {e}")
    except ApiProcessingError as e:
        print(f"Processing failed: {e}")

asyncio.run(main())
```

**Automated file watching:**
```python
import asyncio
from hornet_flow.api import HornetFlowAPI
from hornet_flow.exceptions import ApiFileNotFoundError, ApiInputValueError
import os
from pathlib import Path

async def main():
    api = HornetFlowAPI()

    # Get directories from environment or use defaults
    inputs_dir = os.getenv("INPUTS_DIR", "/shared/inputs")
    work_dir = os.getenv("WORK_DIR", "/shared/work")

    try:
        # Watch for metadata.json files continuously
        await api.workflow.watch(
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

asyncio.run(main())
```

**Single-time processing mode**

```python
import asyncio
from hornet_flow.api import HornetFlowAPI
import os

async def main():
    api = HornetFlowAPI()

    # Process one file and exit (useful for Docker containers)
    try:
        await api.workflow.watch(
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

asyncio.run(main())
```

**Batch processing multiple repositories:**
```python
import asyncio
from hornet_flow.api import HornetFlowAPI

async def main():
    api = HornetFlowAPI()

    repositories = [
        "https://github.com/COSMIIC-Inc/Implantables-Electrodes",
        "https://github.com/CARSSCenter/Sub-mm-Parylene-Cuff-Electrode"
    ]

    for repo_url in repositories:
        try:
            # Process each repository
            success_count, total_count = await api.workflow.run(
                repo_url=repo_url,
                plugin="debug",
                work_dir="/tmp/batch-processing"
            )
            print(f"{repo_url}: {success_count}/{total_count} components processed")
        except Exception as e:
            print(f"Failed to process {repo_url}: {e}")

asyncio.run(main())
```

**Working with existing repositories:**
```python
import asyncio
from hornet_flow.api import HornetFlowAPI

async def main():
    api = HornetFlowAPI()

    # Show manifest contents
    manifest_data = await api.manifest.show("/path/to/local/repo", manifest_type="both")

    if "cad" in manifest_data:
        print("CAD Manifest:")
        print(manifest_data["cad"])

    if "sim" in manifest_data:
        print("SIM Manifest:")
        print(manifest_data["sim"])

    # Load CAD files with filtering
    success_count, total_count = await api.cad.load(
        repo_path="/path/to/local/repo",
        plugin="osparc",
        type_filter="assembly",
        name_filter="electrode"
    )

asyncio.run(main())
```

### Web Framework Integration

The async API integrates seamlessly with modern Python web frameworks:

**FastAPI Integration:**
```python
from fastapi import FastAPI, BackgroundTasks
from hornet_flow.api import HornetFlowAPI

app = FastAPI()
api = HornetFlowAPI()

@app.post("/process-workflow")
async def process_workflow(repo_url: str, plugin: str = "debug"):
    """Process a repository workflow."""
    try:
        success_count, total_count = await api.workflow.run(
            repo_url=repo_url,
            plugin=plugin,
            fail_fast=False
        )
        return {
            "status": "success",
            "success_count": success_count,
            "total_count": total_count
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/validate/{repo_path:path}")
async def validate_manifests(repo_path: str):
    """Validate manifests in a repository."""
    cad_valid, sim_valid = await api.manifest.validate(repo_path)
    return {
        "cad_valid": cad_valid,
        "sim_valid": sim_valid
    }
```

**aiohttp Integration:**
```python
from aiohttp import web
from hornet_flow.api import HornetFlowAPI

api = HornetFlowAPI()

async def process_workflow(request):
    """Process a repository workflow."""
    data = await request.json()
    repo_url = data.get("repo_url")
    plugin = data.get("plugin", "debug")

    try:
        success_count, total_count = await api.workflow.run(
            repo_url=repo_url,
            plugin=plugin
        )
        return web.json_response({
            "status": "success",
            "success_count": success_count,
            "total_count": total_count
        })
    except Exception as e:
        return web.json_response(
            {"status": "error", "message": str(e)},
            status=500
        )

app = web.Application()
app.router.add_post('/process', process_workflow)

if __name__ == "__main__":
    web.run_app(app, host='0.0.0.0', port=8080)
```


## Development workflow

```bash
make help           # Show available targets
make install-all    # Install all dependencies
make lint           # Run linting
make tests          # Run tests
```

## Architecture & Design

### Async-First Design

hornet-flow is built with an **async-first architecture** using Python's `asyncio`:

- **Service Layer**: All I/O operations (file, git, HTTP) use native async libraries
  - `aiofiles` for async file operations
  - `asyncio.subprocess` for git commands
  - `httpx` for async HTTP requests
  - `watchfiles` for async file watching

- **Event System**: `AsyncEventDispatcher` for async event callbacks
  - All callbacks must be async functions
  - Events execute sequentially to maintain workflow order
  - Proper error handling with async context

- **Plugin System**: Abstract plugin interface with async lifecycle
  - `async setup()`: Initialize plugin resources
  - `async load_component()`: Process individual components
  - `async teardown()`: Clean up resources

- **Workflow Orchestration**: Concurrent processing where beneficial
  - Manifest validation runs concurrently for CAD/SIM
  - Sibling components process in parallel
  - Maintains parent→child dependency ordering

- **CLI Layer**: Uses `asyncio.run()` to wrap async API calls
  - Simple synchronous interface for users
  - Internally leverages full async capabilities

### Benefits of Async Design

1. **Concurrent I/O**: File reading, git operations, and HTTP requests don't block
2. **Web Framework Integration**: Seamless integration with FastAPI, aiohttp, etc.
3. **Scalability**: Efficient resource usage for batch operations
4. **Plugin Flexibility**: Plugins can perform async operations (DB, HTTP, etc.)
5. **Event System**: Non-blocking event handlers for workflow coordination
