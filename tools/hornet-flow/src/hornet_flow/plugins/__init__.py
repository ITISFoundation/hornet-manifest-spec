"""Plugin system for hornet-flow manifest processing."""

import importlib
from pathlib import Path
from typing import Dict, Type


def discover_plugins() -> Dict[str, Type]:
    """Discover all available plugins in the plugins directory."""
    from .base import HornetFlowPlugin

    plugins = {}
    plugin_dir = Path(__file__).parent

    for plugin_file in plugin_dir.glob("*_plugin.py"):
        module_name = f"hornet_flow.plugins.{plugin_file.stem}"
        try:
            module = importlib.import_module(module_name)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, HornetFlowPlugin)
                    and attr != HornetFlowPlugin
                ):
                    # Create an instance to get the actual name value
                    try:
                        plugin_instance = attr()
                        plugin_name = plugin_instance.name
                        plugins[plugin_name] = attr
                    except Exception:
                        # If instantiation fails, skip this plugin
                        continue
        except ImportError:
            continue

    return plugins


def get_plugin(plugin_name: str) -> Type:
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
