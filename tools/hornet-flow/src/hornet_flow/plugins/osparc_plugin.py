"""OSparc plugin for loading components into OSparc."""

import contextlib
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

import XCore
import XCoreModeling

from .base import HornetFlowPlugin


@contextmanager
def _app_lifespan() -> Iterator[XCore.ConsoleApp]:
    """Context manager for the lifespan of the OSparc app."""

    TROUBLESOME_PLUGIN_GROUP = (
        "CPythonPlugin",  # will try to reinit python
        "CJosuaUIPlugin",
        "CJosuaPlugin",  # will start ares - bad for testing when don't need ares
        "CSoftwareUpdatePlugin",  # no updates while testing!
        "CXViewsPLugin",  # don't start UI and inject file browser delegate
    )

    OSPARC_TROUBLESOME_UI_PLUGIN_GROUP = (
        # CR->MaG: I had trouble running on linux if this group was only partially
        # present.  Until the gaia runners can handle having XDisplay
        # we need to disable all of these plugin when running tests.  For consistency
        # I also disable them on windows.
        "CXRendererOffscreenPlugin",
        "CModelerHeadlessPlugin",  # needed?
    )

    if XCore.GetApp() is not None:
        return

    old_log_level = XCore.GetLogLevel()
    XCore.SetLogLevel(XCore.eLogCategory.Warning)

    theapp = XCore.GetOrCreateConsoleApp(
        plugin_black_list=list(TROUBLESOME_PLUGIN_GROUP)
        + list(OSPARC_TROUBLESOME_UI_PLUGIN_GROUP)
    )

    assert theapp == XCore.GetApp()
    assert XCoreModeling.GetActiveModel()

    theapp.NewDocument()

    try:
        yield theapp
    finally:
        XCore.SetLogLevel(old_log_level)


@contextmanager
def _app_document_lifespan(app: XCore.ConsoleApp, repo_path: Path) -> Iterator[None]:
    base_dir = repo_path.parent if repo_path else Path.cwd()
    file_name = repo_path.name if repo_path else "hornet-model"
    doc_path = base_dir / f"{file_name}.smash"
    assert base_dir.exists()  # nosec

    app.NewDocument()

    try:
        yield
    finally:
        XCore.GetApp().SaveDocumentAs(f"{doc_path}")


@contextmanager
def _app_document_main_model_group_lifespan(
    repo_name: str,
) -> Iterator[XCoreModeling.EntityGroup]:
    """Context manager for the main model's group lifespan."""

    main_group = XCoreModeling.CreateGroup(repo_name)
    # TODO: add metadata as
    # self._main_group.SetDescription("hornet.repo_path", str(repo_path))

    yield main_group

    # Zoom to main group if succeeds
    with contextlib.suppress(Exception):
        from s4l_v1.renderer import ZoomToEntity

        ZoomToEntity(main_group, zoom_factor=1.2)


class OSparcPlugin(HornetFlowPlugin):
    """Plugin for loading components into OSparc."""

    def __init__(self):
        self._name = "osparc"
        self._logger: logging.Logger = logging.getLogger(__name__)
        self._repo_path: Optional[Path] = None
        self._manifest_path: Optional[Path] = None

        # XCore / OSparc specific attributes
        self._main_group: Optional[XCoreModeling.EntityGroup] = (
            None  # XCoreModeling.EntityGroup when available
        )
        self._loaded_groups: list[
            XCoreModeling.EntityGroup
        ] = []  # Track loaded groups for cleanup

        self._stack = contextlib.ExitStack()

    @property
    def name(self) -> str:
        """Plugin name for CLI selection."""
        return self._name

    def setup(
        self, repo_path: Path, manifest_path: Path, logger: logging.Logger
    ) -> None:
        """Initialize OSparc plugin."""
        self._logger = logger
        self._repo_path = repo_path
        self._manifest_path = manifest_path

        # setup lifespan contexts
        self._logger.info("🛠 Setting up OSparc plugin")

        app = self._stack.enter_context(_app_lifespan())
        # TODO: log info about app, model, etc

        self._stack.enter_context(_app_document_lifespan(app, repo_path))
        self._main_group = self._stack.enter_context(
            _app_document_main_model_group_lifespan(repo_path.stem)
        )

    def load_component(
        self,
        component_id: str,
        component_type: str,
        component_description: Optional[str],
        component_files: list[Path],  # these are verified paths!!
        component_parent_id: list[str],
    ) -> bool:
        """Load component into OSparc."""
        try:
            # 1. Create a group for the component and set name
            component_group = XCoreModeling.CreateGroup(component_id)

            # 2. Save metadata in Group name Properties
            # TODO: add all headers of manifest or even the entire manifest as JSON?
            component_group.SetDescription("hornet.description", component_description)
            component_group.SetDescription("hornet.component_id", component_id)
            component_group.SetDescription("hornet.component_type", component_type)

            # 3. Load component trying at least one of the provided files
            is_file_imported = False
            for component_path in component_files:
                try:
                    imported_entities = XCoreModeling.Import(str(component_path))

                except Exception:  # pylint: disable=broad-exception-caught
                    # FIXME: should be exceptionr elated with Import, not path existence etc
                    self._logger.warning(
                        "Cannot import %s, let's check next ...", component_path
                    )

                else:
                    component_group.Add(imported_entities)
                    self._logger.info(
                        "Successfully imported %d entities for component %s using %s",
                        len(imported_entities),
                        component_id,
                        component_path,
                    )
                    is_file_imported = True
                    break

            if not is_file_imported:
                raise FileNotFoundError(
                    f"No valid files could be loaded for component '{component_id}'"
                )

            # 4. Add component_group to main group or parent group
            assert self._main_group  # nosec

            if not component_parent_id:
                self._main_group.Add(component_group)
                return True

            # Search for parent group in loaded groups
            # TODO: search in tree by path, not just last id
            parent_component_id = (
                component_parent_id[-1] if component_parent_id else None
            )
            parent_group = next(
                (
                    grp
                    for grp in self._loaded_groups
                    if grp.GetDescription("hornet.component_id") == parent_component_id
                ),
                None,
            )
            if not parent_group:
                parent_group = self._main_group

            parent_group.Add(component_group)
            self._logger.debug(
                "Added group '%s' to parent group '%s'",
                component_group.Name,
                parent_group.Name,
            )

            self._loaded_groups.append(component_group)

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            self._logger.exception("Failed to load component %s: %s", component_id, e)
            return False

    def teardown(self) -> None:
        """Clean up OSparc resources."""
        self._stack.close()

        # Reset state
        self._loaded_groups.clear()
        self._main_group = None
