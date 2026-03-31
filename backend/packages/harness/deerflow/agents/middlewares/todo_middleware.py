"""Middleware that extends TodoListMiddleware with context-loss detection.

When the message history is truncated (e.g., by SummarizationMiddleware), the
original `write_todos` tool call and its ToolMessage can be scrolled out of the
active context window. This middleware detects that situation and injects a
reminder message so the model still knows about the outstanding todo list.

This patched version also fixes the "multiple non-consecutive system messages" issue
by properly merging system message content instead of creating new system messages.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast, override

from langchain.agents.middleware import TodoListMiddleware
from langchain.agents.middleware.todo import PlanningState, Todo
from langchain.agents.middleware.types import ModelCallResult, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.runtime import Runtime


def _todos_in_messages(messages: list[Any]) -> bool:
    """Return True if any AIMessage in *messages* contains a write_todos tool call."""
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc.get("name") == "write_todos":
                    return True
    return False


def _reminder_in_messages(messages: list[Any]) -> bool:
    """Return True if a todo_reminder HumanMessage is already present in *messages*."""
    for msg in messages:
        if isinstance(msg, HumanMessage) and getattr(msg, "name", None) == "todo_reminder":
            return True
    return False


def _format_todos(todos: list[Todo]) -> str:
    """Format a list of Todo items into a human-readable string."""
    lines: list[str] = []
    for todo in todos:
        status = todo.get("status", "pending")
        content = todo.get("content", "")
        lines.append(f"- [{status}] {content}")
    return "\n".join(lines)


class TodoMiddleware(TodoListMiddleware):
    """Extends TodoListMiddleware with `write_todos` context-loss detection.

    When the original `write_todos` tool call has been truncated from the message
    history (e.g., after summarization), the model loses awareness of the current
    todo list. This middleware detects that gap in `before_model` / `abefore_model`
    and injects a reminder message so the model can continue tracking progress.

    This patched version also overrides wrap_model_call and awrap_model_call to fix
    the "multiple non-consecutive system messages" error with Anthropic's API by
    properly merging system message content instead of creating new system messages.
    """

    @override
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelCallResult:
        """Update the system message by merging content (Anthropic-compatible).

        Instead of creating a new SystemMessage (which causes "multiple non-consecutive
        system messages" errors), this merges the todo prompt into the existing system
        message content blocks.
        """
        if request.system_message is not None:
            # Merge with existing system message
            new_system_content = [
                *request.system_message.content_blocks,
                {"type": "text", "text": f"\n\n{self.system_prompt}"},
            ]
        else:
            # Create initial system message
            new_system_content = [{"type": "text", "text": self.system_prompt}]

        # Create new system message with merged content
        new_system_message = SystemMessage(
            content=cast("list[str | dict[str, str]]", new_system_content)
        )

        # Pass the merged system message to the handler
        return handler(request.override(system_message=new_system_message))

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        """Update the system message by merging content (async, Anthropic-compatible).

        Instead of creating a new SystemMessage (which causes "multiple non-consecutive
        system messages" errors), this merges the todo prompt into the existing system
        message content blocks.
        """
        if request.system_message is not None:
            # Merge with existing system message
            new_system_content = [
                *request.system_message.content_blocks,
                {"type": "text", "text": f"\n\n{self.system_prompt}"},
            ]
        else:
            # Create initial system message
            new_system_content = [{"type": "text", "text": self.system_prompt}]

        # Create new system message with merged content
        new_system_message = SystemMessage(
            content=cast("list[str | dict[str, str]]", new_system_content)
        )

        # Pass the merged system message to the handler
        return await handler(request.override(system_message=new_system_message))

    @override
    def before_model(
        self,
        state: PlanningState,
        runtime: Runtime,  # noqa: ARG002
    ) -> dict[str, Any] | None:
        """Inject a todo-list reminder when write_todos has left the context window."""
        todos: list[Todo] = state.get("todos") or []  # type: ignore[assignment]
        if not todos:
            return None

        messages = state.get("messages") or []
        if _todos_in_messages(messages):
            # write_todos is still visible in context — nothing to do.
            return None

        if _reminder_in_messages(messages):
            # A reminder was already injected and hasn't been truncated yet.
            return None

        # The todo list exists in state but the original write_todos call is gone.
        # Inject a reminder as a HumanMessage so the model stays aware.
        formatted = _format_todos(todos)
        reminder = HumanMessage(
            name="todo_reminder",
            content=(
                "<system_reminder>\n"
                "Your todo list from earlier is no longer visible in the current context window, "
                "but it is still active. Here is the current state:\n\n"
                f"{formatted}\n\n"
                "Continue tracking and updating this todo list as you work. "
                "Call `write_todos` whenever the status of any item changes.\n"
                "</system_reminder>"
            ),
        )
        return {"messages": [reminder]}

    @override
    async def abefore_model(
        self,
        state: PlanningState,
        runtime: Runtime,
    ) -> dict[str, Any] | None:
        """Async version of before_model."""
        return self.before_model(state, runtime)
