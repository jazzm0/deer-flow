"""Middleware to fix dangling tool calls in message history.

A dangling tool call occurs when an AIMessage contains tool_calls but there are
no corresponding ToolMessages in the history (e.g., due to user interruption or
request cancellation). This causes LLM errors due to incomplete message format.

This middleware intercepts the model call to detect and patch such gaps by
inserting synthetic ToolMessages with an error indicator immediately after the
AIMessage that made the tool calls, ensuring correct message ordering.

Note: Uses wrap_model_call instead of before_model to ensure patches are inserted
at the correct positions (immediately after each dangling AIMessage), not appended
to the end of the message list as before_model + add_messages reducer would do.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelCallResult, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, ToolMessage

logger = logging.getLogger(__name__)


class DanglingToolCallMiddleware(AgentMiddleware[AgentState]):
    """Inserts placeholder ToolMessages for dangling tool calls before model invocation.

    Scans the message history for AIMessages whose tool_calls lack corresponding
    ToolMessages, and injects synthetic error responses immediately after the
    offending AIMessage so the LLM receives a well-formed conversation.
    """

    @staticmethod
    def _extract_tool_call_ids(msg: AIMessage) -> list[tuple[str, str]]:
        """Extract (id, name) pairs from all tool call representations in an AIMessage.

        Handles three storage locations:
          1. msg.tool_calls — standard LangChain list of dicts
          2. msg.additional_kwargs["tool_use"] — raw Anthropic streaming blocks (list)
          3. msg.additional_kwargs["tool_calls"] — OpenAI-style fallback (list)
        """
        results: list[tuple[str, str]] = []
        seen: set[str] = set()

        def _add(tc_id: str | None, tc_name: str) -> None:
            if tc_id and tc_id not in seen:
                seen.add(tc_id)
                results.append((tc_id, tc_name))

        for tc in getattr(msg, "tool_calls", None) or []:
            _add(tc.get("id"), tc.get("name", "unknown"))

        extra = getattr(msg, "additional_kwargs", {}) or {}

        for block in extra.get("tool_use", None) or []:
            if isinstance(block, dict):
                _add(block.get("id"), block.get("name", "unknown"))

        for tc in extra.get("tool_calls", None) or []:
            if isinstance(tc, dict):
                fn = tc.get("function", {}) or {}
                _add(tc.get("id"), fn.get("name", "unknown"))

        return results

    def _build_patched_messages(self, messages: list) -> list | None:
        """Return a new message list with patches inserted at the correct positions.

        For each AIMessage with dangling tool_calls (no corresponding ToolMessage),
        a synthetic ToolMessage is inserted immediately after that AIMessage.
        Returns None if no patches are needed.
        """
        # Collect IDs of all existing ToolMessages
        existing_tool_msg_ids: set[str] = set()
        for msg in messages:
            if isinstance(msg, ToolMessage):
                existing_tool_msg_ids.add(msg.tool_call_id)

        # Check if any patching is needed
        needs_patch = False
        for msg in messages:
            if not isinstance(msg, AIMessage):
                continue
            extracted = self._extract_tool_call_ids(msg)
            logger.debug(
                f"DanglingToolCallMiddleware: AIMessage id={getattr(msg, 'id', '?')} "
                f"tool_calls={[tc.get('id') for tc in (getattr(msg, 'tool_calls', None) or [])]} "
                f"additional_kwargs_keys={list((getattr(msg, 'additional_kwargs', None) or {}).keys())} "
                f"extracted_ids={[tc_id for tc_id, _ in extracted]}"
            )
            for tc_id, _ in extracted:
                if tc_id not in existing_tool_msg_ids:
                    needs_patch = True
                    break
            if needs_patch:
                break

        if not needs_patch:
            logger.debug(f"DanglingToolCallMiddleware: no dangling tool calls found (existing_tool_msg_ids={existing_tool_msg_ids})")
            return None

        # Build new list with patches inserted right after each dangling AIMessage
        patched: list = []
        patched_ids: set[str] = set()
        patch_count = 0
        for msg in messages:
            patched.append(msg)
            if not isinstance(msg, AIMessage):
                continue
            for tc_id, tc_name in self._extract_tool_call_ids(msg):
                if tc_id not in existing_tool_msg_ids and tc_id not in patched_ids:
                    patched.append(
                        ToolMessage(
                            content="[Tool call was interrupted and did not return a result.]",
                            tool_call_id=tc_id,
                            name=tc_name,
                            status="error",
                        )
                    )
                    patched_ids.add(tc_id)
                    patch_count += 1

        logger.warning(f"Injecting {patch_count} placeholder ToolMessage(s) for dangling tool calls")
        return patched

    @override
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelCallResult:
        patched = self._build_patched_messages(request.messages)
        if patched is not None:
            request = request.override(messages=patched)
        return handler(request)

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        patched = self._build_patched_messages(request.messages)
        if patched is not None:
            request = request.override(messages=patched)
        return await handler(request)
