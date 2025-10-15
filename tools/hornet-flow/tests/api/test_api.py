# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=unused-variable


from hornet_flow.api import EventDispatcher, HornetFlowAPI, WorkflowEvent


def test_api_initialization() -> None:
    """Test that the API initializes correctly with all sub-APIs."""
    api = HornetFlowAPI()

    assert hasattr(api, "workflow")
    assert hasattr(api, "repo")
    assert hasattr(api, "manifest")
    assert hasattr(api, "cad")


def test_event_system_imports() -> None:
    """Test that event system components are properly imported."""
    assert EventDispatcher is not None
    assert WorkflowEvent is not None
    assert WorkflowEvent.MANIFESTS_READY is not None


def test_api_info() -> None:
    """Test that API info method returns expected system information."""
    api = HornetFlowAPI()
    info = api.info()

    # Verify expected keys are present
    assert "version" in info
    assert "python_version" in info
    assert "platform" in info
    assert "git_version" in info
    assert "default_plugin" in info
    assert "plugins" in info
    assert "configuration" in info
    assert "environment" in info

    # Verify types
    assert isinstance(info["version"], str)
    assert isinstance(info["python_version"], str)
    assert isinstance(info["platform"], str)
    assert isinstance(info["git_version"], (str, bool))
    assert isinstance(info["default_plugin"], str)
    assert isinstance(info["plugins"], dict)
    assert isinstance(info["configuration"], dict)
    assert isinstance(info["environment"], dict)

    # Verify configuration structure
    config = info["configuration"]
    assert "package_location" in config
    assert "plugin_directory" in config
    assert "plugin_directory_exists" in config
    assert "temp_directory" in config
    assert isinstance(config["plugin_directory_exists"], bool)
