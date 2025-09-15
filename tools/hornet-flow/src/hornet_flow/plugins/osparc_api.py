import json
import logging
from pathlib import Path
from typing import Any

import XCoreModeling

_logger = logging.getLogger(__name__)


def load_component(
    component: dict[str, Any],
    parent_group: XCoreModeling.EntityGroup | None = None,
    base_path: str = ".",
    type_filter: str | None = None,
    name_filter: str | None = None,
) -> XCoreModeling.EntityGroup | None:
    # Check type filter
    if type_filter is not None and component.get("type") != type_filter:
        _logger.info(
            "Skipping component '%s' due to type filter (type: %s, filter: %s)",
            component["id"],
            component.get("type"),
            type_filter,
        )
        return None

    # Check name filter
    if name_filter is not None and name_filter.lower() not in component["id"].lower():
        _logger.info(
            "Skipping component '%s' due to name filter (filter: %s)",
            component["id"],
            name_filter,
        )
        return None

    component_group = XCoreModeling.CreateGroup(component["id"])

    if "description" in component:
        component_group.SetDescription("description", component["description"])

    if parent_group is not None:
        parent_group.Add(component_group)

    _logger.info(
        "Processing component: %s (type: %s)",
        component["id"],
        component.get("type", "unknown"),
    )

    if "files" in component:
        for file_info in component["files"]:
            file_path = Path(base_path) / file_info["path"]

            try:
                if file_path.exists():
                    _logger.info("Importing file: %s", file_path)
                    imported_entities = XCoreModeling.Import(str(file_path))

                    for entity in imported_entities:
                        component_group.Add(entity)

                    _logger.info(
                        "Successfully imported %d entities", len(imported_entities)
                    )
                else:
                    _logger.warning("File not found: %s", file_path)

            except Exception as e:  # pylint: disable=broad-exception-caught
                _logger.error("Error importing %s: %s", file_path, str(e))

    if "components" in component:
        for nested_component in component["components"]:
            nested_result = load_component(
                nested_component, component_group, base_path, type_filter, name_filter
            )
            # If nested component was filtered out but current component has no other content,
            # we might want to consider if this component should exist

    return component_group


def load_cad_manifest(
    manifest: dict[str, Any],
    base_path: str = ".",
    type_filter: str | None = None,
    name_filter: str | None = None,
) -> list[XCoreModeling.EntityGroup]:
    _logger.info("Starting CAD manifest loading...")
    if type_filter:
        _logger.info("Filtering by type: %s", type_filter)
    if name_filter:
        _logger.info("Filtering by name: %s", name_filter)

    loaded_components = []

    for component in manifest.get("components", []):
        try:
            component_group = load_component(
                component, None, base_path, type_filter, name_filter
            )
            if component_group is not None:
                loaded_components.append(component_group)
        except Exception as e:  # pylint: disable=broad-exception-caught
            _logger.error(
                "Error loading component %s: %s", component.get("id", "unknown"), str(e)
            )

    _logger.info("Completed loading %d top-level components", len(loaded_components))
    return loaded_components


def _zoom_loaded_components(components: list[XCoreModeling.EntityGroup]) -> None:
    from s4l_v1.renderer import ZoomToEntity

    if not components:
        _logger.warning("No components to zoom to.")
        return

    ZoomToEntity(components, zoom_factor=1.2)


def _load_manifest_from_file(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found at {manifest_path}")

    try:
        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)

    except json.JSONDecodeError as e:
        msg = f"Error parsing JSON from {manifest_path}: {e}"
        raise ValueError(msg) from e
    except Exception as e:
        msg = f"Error reading manifest file {manifest_path}: {e}"
        raise RuntimeError(msg) from e


def main(
    manifest_file: str,
    work_dir: Path | None = None,
    type_filter: str | None = None,
    name_filter: str | None = None,
) -> None:
    try:
        model = XCoreModeling.GetActiveModel()
        if model is None:
            _logger.error(
                "No active model found. Please ensure XCoreModeling is properly initialized."
            )
            return

        _logger.info("Using active model: %s", model.Name)

        if work_dir is None:
            work_dir = Path(__file__).parent

        _logger.info("Working path for file resolution: %s", work_dir)

        manifest_path = work_dir / manifest_file
        manifest = _load_manifest_from_file(manifest_path)

        loaded_components = load_cad_manifest(
            manifest, str(work_dir), type_filter, name_filter
        )

        if loaded_components:
            main_group = XCoreModeling.CreateGroup("CAD_Manifest_Components")
            for component in loaded_components:
                main_group.Add(component)

            _logger.info(
                "Created main group '%s' containing all loaded components",
                main_group.Name,
            )

            _zoom_loaded_components(main_group)

    except Exception as e:
        _logger.error("Fatal error: %s", str(e))
        raise
