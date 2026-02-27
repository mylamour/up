"""Plugin-EventBridge integration.

Connects the PluginRegistry's hooks to the EventBridge so that
plugin hooks fire automatically when matching events are emitted.
"""

import logging
from pathlib import Path

from up.events import Event, EventBridge, EventType
from up.plugins.hooks import HookResult, HookRunner, HookSpec, load_hooks_from_json
from up.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)

# Map EventType values to hook event names used in hooks.json
EVENT_TYPE_MAP = {
    EventType.PRE_TOOL_USE: "pre_tool_use",
    EventType.POST_TOOL_USE: "post_tool_use",
    EventType.PRE_EXECUTE: "pre_execute",
    EventType.POST_EXECUTE: "post_execute",
    EventType.TASK_START: "task_start",
    EventType.TASK_COMPLETE: "task_complete",
    EventType.TASK_FAILED: "task_failed",
}


class PluginEventBridge:
    """Connects plugin hooks to the EventBridge.

    Loads hooks from all enabled plugins and registers them as
    EventBridge handlers. When events fire, matching hooks execute
    via HookRunner.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self._registry = PluginRegistry(workspace)
        self._runner = HookRunner(workspace)
        self._hook_map: dict[str, list[HookSpec]] = {}
        self._bridge: EventBridge | None = None

    def initialize(self) -> None:
        """Load plugins and register hooks with EventBridge."""
        self._registry.load()
        self._load_plugin_hooks()
        self._register_with_bridge()

    def _load_plugin_hooks(self) -> None:
        """Load hook specs from all enabled plugins."""
        self._hook_map.clear()

        for plugin in self._registry.get_enabled():
            for hook_path in plugin.components.hooks:
                if hook_path.name == "hooks.json":
                    specs = load_hooks_from_json(hook_path)
                    for spec in specs:
                        # Resolve relative commands to plugin directory
                        if not spec.command.startswith("/"):
                            spec.command = f"cd {plugin.path} && {spec.command}"
                        # Group by event type from matcher or default to all
                        event_key = self._event_key_from_spec(spec)
                        self._hook_map.setdefault(event_key, []).append(spec)

        total = sum(len(v) for v in self._hook_map.values())
        if total:
            logger.info("Loaded %d plugin hooks from %d event types",
                        total, len(self._hook_map))

    def _event_key_from_spec(self, spec: HookSpec) -> str:
        """Determine which event type a hook should bind to.

        If the matcher contains an event type name, use that.
        Otherwise default to 'all' (fires on every hookable event).
        """
        if spec.matcher:
            for event_name in EVENT_TYPE_MAP.values():
                if event_name in spec.matcher:
                    return event_name
        return "all"

    def _register_with_bridge(self) -> None:
        """Subscribe to hookable EventBridge events."""
        self._bridge = EventBridge(self.workspace)

        for event_type in EVENT_TYPE_MAP:
            self._bridge.subscribe(event_type, self._make_handler(event_type))

    def _make_handler(self, event_type: EventType):
        """Create an event handler that runs matching plugin hooks."""
        event_name = EVENT_TYPE_MAP[event_type]

        def handler(event: Event) -> None:
            # Collect hooks for this specific event + "all" hooks
            specs = list(self._hook_map.get(event_name, []))
            specs.extend(self._hook_map.get("all", []))

            if not specs:
                return

            event_data = {
                "event_type": event_name,
                **event.data,
            }

            results = self._runner.run_hooks(specs, event_data)
            self._log_results(event_name, results)

            # If any hook blocked, mark the event
            if self._runner.is_blocked(results):
                event.data["_blocked"] = True
                event.data["_block_reasons"] = self._runner.get_block_messages(results)

        return handler

    def _log_results(self, event_name: str, results: list[HookResult]) -> None:
        """Log hook execution results."""
        for r in results:
            if r.exit_code == 0 and "skipped" not in r.message:
                logger.debug("Hook [%s] %s: %s", event_name, r.hook_name, r.message)
            elif r.exit_code == 1:
                logger.warning("Hook warning [%s] %s: %s",
                               event_name, r.hook_name, r.message)
            elif not r.allowed:
                logger.error("Hook BLOCKED [%s] %s: %s",
                             event_name, r.hook_name, r.message)

    def is_event_blocked(self, event: Event) -> bool:
        """Check if an event was blocked by any plugin hook."""
        return event.data.get("_blocked", False)

    def get_block_reasons(self, event: Event) -> list[str]:
        """Get block reasons from an event."""
        return event.data.get("_block_reasons", [])
