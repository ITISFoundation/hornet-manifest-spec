# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=unused-variable

import pytest

from hornet_flow.api import EventDispatcher, HornetFlowAPI, WorkflowEvent


def test_api_initialization() -> None:
    """Test that the API initializes correctly with all sub-APIs."""
    api = HornetFlowAPI()
    
    assert hasattr(api, 'workflow')
    assert hasattr(api, 'repo')
    assert hasattr(api, 'manifest')
    assert hasattr(api, 'cad')


def test_event_system_imports() -> None:
    """Test that event system components are properly imported."""
    assert EventDispatcher is not None
    assert WorkflowEvent is not None
    assert WorkflowEvent.BEFORE_PROCESS_MANIFEST is not None
