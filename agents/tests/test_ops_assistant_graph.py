"""Tests for ops assistant graph and event streaming."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRunAssistantStreaming:
    """Tests for run_assistant event streaming."""

    @pytest.mark.asyncio
    async def test_streaming_yields_response_event(self):
        """Streaming mode yields final response event."""
        with patch("src.graphs.ops_assistant_graph.get_settings") as mock_settings:
            mock_settings.return_value.pg_dsn = "postgresql://test"

            with patch("src.graphs.ops_assistant_graph.AsyncPostgresSaver") as mock_saver:
                # Mock the checkpointer context manager
                mock_checkpointer = AsyncMock()
                mock_saver.from_conn_string.return_value.__aenter__ = AsyncMock(return_value=mock_checkpointer)
                mock_saver.from_conn_string.return_value.__aexit__ = AsyncMock()

                with patch("src.graphs.ops_assistant_graph.create_workflow") as mock_workflow:
                    # Mock the graph to return a simple response
                    mock_graph = AsyncMock()

                    # Simulate agent producing a response
                    from langchain_core.messages import AIMessage
                    async def mock_astream(*args, **kwargs):
                        yield {"agent": {"messages": [AIMessage(content="Test response")]}}

                    mock_graph.astream = mock_astream
                    mock_workflow.return_value.compile.return_value = mock_graph

                    from src.graphs.ops_assistant_graph import run_assistant

                    events = []
                    async for event_type, data in run_assistant("test message", stream_events=True):
                        events.append((event_type, data))

                    # Should yield final response
                    assert len(events) == 1
                    assert events[0][0] == "response"
                    assert events[0][1] == "Test response"

    @pytest.mark.asyncio
    async def test_streaming_yields_tool_call_events(self):
        """Streaming mode yields tool_call events for tool invocations."""
        with patch("src.graphs.ops_assistant_graph.get_settings") as mock_settings:
            mock_settings.return_value.pg_dsn = "postgresql://test"

            with patch("src.graphs.ops_assistant_graph.AsyncPostgresSaver") as mock_saver:
                mock_checkpointer = AsyncMock()
                mock_saver.from_conn_string.return_value.__aenter__ = AsyncMock(return_value=mock_checkpointer)
                mock_saver.from_conn_string.return_value.__aexit__ = AsyncMock()

                with patch("src.graphs.ops_assistant_graph.create_workflow") as mock_workflow:
                    mock_graph = AsyncMock()

                    from langchain_core.messages import AIMessage, ToolMessage
                    async def mock_astream(*args, **kwargs):
                        # Agent decides to call a tool
                        ai_msg = AIMessage(content="", tool_calls=[
                            {"name": "search_orders", "args": {"query": "test"}}
                        ])
                        yield {"agent": {"messages": [ai_msg]}}

                        # Tool returns result
                        tool_msg = ToolMessage(content="Tool result", tool_call_id="123")
                        yield {"tools": {"messages": [tool_msg]}}

                        # Agent produces final response
                        final_msg = AIMessage(content="Final answer")
                        yield {"agent": {"messages": [final_msg]}}

                    mock_graph.astream = mock_astream
                    mock_workflow.return_value.compile.return_value = mock_graph

                    from src.graphs.ops_assistant_graph import run_assistant

                    events = []
                    async for event_type, data in run_assistant("test", stream_events=True):
                        events.append((event_type, data))

                    # Should have tool_call, tool_result, and response events
                    assert len(events) == 3
                    assert events[0][0] == "tool_call"
                    assert events[0][1]["name"] == "search_orders"
                    assert events[0][1]["args"] == {"query": "test"}
                    assert events[1][0] == "tool_result"
                    assert events[2][0] == "response"
                    assert events[2][1] == "Final answer"

    @pytest.mark.asyncio
    async def test_streaming_handles_errors_gracefully(self):
        """Streaming mode handles errors and yields error event."""
        with patch("src.graphs.ops_assistant_graph.get_settings") as mock_settings:
            mock_settings.return_value.pg_dsn = "postgresql://test"

            with patch("src.graphs.ops_assistant_graph.AsyncPostgresSaver") as mock_saver:
                mock_checkpointer = AsyncMock()
                mock_saver.from_conn_string.return_value.__aenter__ = AsyncMock(return_value=mock_checkpointer)
                mock_saver.from_conn_string.return_value.__aexit__ = AsyncMock()

                with patch("src.graphs.ops_assistant_graph.create_workflow") as mock_workflow:
                    mock_graph = AsyncMock()

                    # Simulate an error during streaming
                    async def mock_astream(*args, **kwargs):
                        raise RuntimeError("Test error")

                    mock_graph.astream = mock_astream
                    mock_workflow.return_value.compile.return_value = mock_graph

                    from src.graphs.ops_assistant_graph import run_assistant

                    events = []
                    async for event_type, data in run_assistant("test", stream_events=True):
                        events.append((event_type, data))

                    # Should yield error event and final response
                    assert len(events) == 2
                    assert events[0][0] == "error"
                    assert "Test error" in events[0][1]["message"]
                    assert events[1][0] == "response"
                    assert "error occurred" in events[1][1].lower()

    @pytest.mark.asyncio
    async def test_non_streaming_yields_only_response(self):
        """Non-streaming mode yields only final response event."""
        with patch("src.graphs.ops_assistant_graph.get_settings") as mock_settings:
            mock_settings.return_value.pg_dsn = "postgresql://test"

            with patch("src.graphs.ops_assistant_graph.AsyncPostgresSaver") as mock_saver:
                mock_checkpointer = AsyncMock()
                mock_saver.from_conn_string.return_value.__aenter__ = AsyncMock(return_value=mock_checkpointer)
                mock_saver.from_conn_string.return_value.__aexit__ = AsyncMock()

                with patch("src.graphs.ops_assistant_graph.create_workflow") as mock_workflow:
                    mock_graph = AsyncMock()

                    from langchain_core.messages import AIMessage, HumanMessage
                    # Mock ainvoke to return a final state
                    mock_graph.ainvoke = AsyncMock(return_value={
                        "messages": [
                            HumanMessage(content="test"),
                            AIMessage(content="Test response")
                        ],
                        "iteration": 1
                    })

                    mock_workflow.return_value.compile.return_value = mock_graph

                    from src.graphs.ops_assistant_graph import run_assistant

                    events = []
                    async for event_type, data in run_assistant("test", stream_events=False):
                        events.append((event_type, data))

                    # Should only yield final response
                    assert len(events) == 1
                    assert events[0][0] == "response"
                    assert events[0][1] == "Test response"

    @pytest.mark.asyncio
    async def test_non_streaming_handles_errors(self):
        """Non-streaming mode handles errors gracefully."""
        with patch("src.graphs.ops_assistant_graph.get_settings") as mock_settings:
            mock_settings.return_value.pg_dsn = "postgresql://test"

            with patch("src.graphs.ops_assistant_graph.AsyncPostgresSaver") as mock_saver:
                mock_checkpointer = AsyncMock()
                mock_saver.from_conn_string.return_value.__aenter__ = AsyncMock(return_value=mock_checkpointer)
                mock_saver.from_conn_string.return_value.__aexit__ = AsyncMock()

                with patch("src.graphs.ops_assistant_graph.create_workflow") as mock_workflow:
                    mock_graph = AsyncMock()

                    # Simulate error in ainvoke
                    mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("Test error"))
                    mock_workflow.return_value.compile.return_value = mock_graph

                    from src.graphs.ops_assistant_graph import run_assistant

                    events = []
                    async for event_type, data in run_assistant("test", stream_events=False):
                        events.append((event_type, data))

                    # Should yield error event and final response
                    assert len(events) == 2
                    assert events[0][0] == "error"
                    assert "Test error" in events[0][1]["message"]
                    assert events[1][0] == "response"
                    assert "error occurred" in events[1][1].lower()

    @pytest.mark.asyncio
    async def test_streaming_handles_no_final_response(self):
        """Streaming mode handles case where agent produces no response."""
        with patch("src.graphs.ops_assistant_graph.get_settings") as mock_settings:
            mock_settings.return_value.pg_dsn = "postgresql://test"

            with patch("src.graphs.ops_assistant_graph.AsyncPostgresSaver") as mock_saver:
                mock_checkpointer = AsyncMock()
                mock_saver.from_conn_string.return_value.__aenter__ = AsyncMock(return_value=mock_checkpointer)
                mock_saver.from_conn_string.return_value.__aexit__ = AsyncMock()

                with patch("src.graphs.ops_assistant_graph.create_workflow") as mock_workflow:
                    mock_graph = AsyncMock()

                    # Stream completes but no final response
                    async def mock_astream(*args, **kwargs):
                        # Simulate agent running but not producing content
                        from langchain_core.messages import AIMessage
                        yield {"agent": {"messages": [AIMessage(content="")]}}

                    mock_graph.astream = mock_astream
                    mock_workflow.return_value.compile.return_value = mock_graph

                    from src.graphs.ops_assistant_graph import run_assistant

                    events = []
                    async for event_type, data in run_assistant("test", stream_events=True):
                        events.append((event_type, data))

                    # Should yield fallback response
                    assert len(events) == 1
                    assert events[0][0] == "response"
                    assert events[0][1] == "I couldn't complete that request."

    @pytest.mark.asyncio
    async def test_streaming_handles_tool_call_objects(self):
        """Streaming mode handles tool calls as objects (not just dicts)."""
        with patch("src.graphs.ops_assistant_graph.get_settings") as mock_settings:
            mock_settings.return_value.pg_dsn = "postgresql://test"

            with patch("src.graphs.ops_assistant_graph.AsyncPostgresSaver") as mock_saver:
                mock_checkpointer = AsyncMock()
                mock_saver.from_conn_string.return_value.__aenter__ = AsyncMock(return_value=mock_checkpointer)
                mock_saver.from_conn_string.return_value.__aexit__ = AsyncMock()

                with patch("src.graphs.ops_assistant_graph.create_workflow") as mock_workflow:
                    mock_graph = AsyncMock()

                    from langchain_core.messages import AIMessage
                    async def mock_astream(*args, **kwargs):
                        # Create a tool call as an object (not a dict)
                        class ToolCall:
                            def __init__(self):
                                self.name = "search_inventory"
                                self.args = {"query": "milk", "store_id": "store:BK-01"}

                        ai_msg = AIMessage(content="", tool_calls=[ToolCall()])
                        yield {"agent": {"messages": [ai_msg]}}

                        # Final response
                        yield {"agent": {"messages": [AIMessage(content="Found items")]}}

                    mock_graph.astream = mock_astream
                    mock_workflow.return_value.compile.return_value = mock_graph

                    from src.graphs.ops_assistant_graph import run_assistant

                    events = []
                    async for event_type, data in run_assistant("test", stream_events=True):
                        events.append((event_type, data))

                    # Should handle object-based tool calls
                    assert len(events) == 2
                    assert events[0][0] == "tool_call"
                    assert events[0][1]["name"] == "search_inventory"
                    assert events[0][1]["args"]["query"] == "milk"
                    assert events[1][0] == "response"
