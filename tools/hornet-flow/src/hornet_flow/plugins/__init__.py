"""Plugin system for hornet-flow manifest processing."""

import importlib
from pathlib import Path
from typing import Dict, Type

from .base import HornetFlowPlugin


def discover_plugins() -> Dict[str, Type[HornetFlowPlugin]]:
    """Discover all available plugins in the plugins directory."""
    plugins = {}
    plugin_dir = Path(__file__).parent

    for plugin_file in plugin_dir.glob("*_plugin.py"):
        module_name = f"hornet_flow.plugins.{plugin_file.stem}"
        try:
            module = importlib.import_module(module_name)
            for attr_name in dir(module):
                attr_obj = getattr(module, attr_name)
                if (
                    isinstance(attr_obj, type)
                    and issubclass(attr_obj, HornetFlowPlugin)
                    and attr_obj != HornetFlowPlugin
                ):
                    plugins[attr_obj.name] = attr_obj
        except ImportError:
            continue

    return plugins


def get_plugin(plugin_name: str) -> Type[HornetFlowPlugin]:
    """Get plugin class by name."""
    plugins = discover_plugins()
    if plugin_name not in plugins:
        available = ", ".join(plugins.keys())
        raise ValueError(f"Plugin '{plugin_name}' not found. Available: {available}")
    return plugins[plugin_name]


def get_default_plugin() -> str:
    """Get the default plugin name."""
    return "debug"


def list_available_plugins() -> list[str]:
    """List all available plugin names."""
    return list(discover_plugins().keys())
