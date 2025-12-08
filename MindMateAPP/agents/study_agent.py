"""
Study Agent - Main LangGraph Implementation
Intelligent routing and workflow orchestration for student support
"""

import logging
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .agent_state import StudyAgentState, create_initial_state
from .agent_nodes import StudyAgentNodes

logger = logging.getLogger(__name__)


class StudyAgent:
    """
    Study Agent with LangGraph workflow orchestration

    The agent intelligently routes student requests to appropriate
    processing nodes based on intent classification.
    """

    def __init__(self):
        """Initialize Study Agent with LangGraph"""
        self.nodes = StudyAgentNodes()
        self.graph = None
        self.compiled_graph = None
        self._build_graph()

    def _build_graph(self):
        """Build the LangGraph workflow"""
        logger.info("🏗️ Building Study Agent graph...")

        # Create workflow
        workflow = StateGraph(StudyAgentState)

        # Add nodes
        workflow.add_node("classify_intent", self.nodes.classify_intent)
        workflow.add_node("retrieve_context", self.nodes.retrieve_context)
        workflow.add_node("generate_quiz", self.nodes.generate_quiz)
        workflow.add_node("answer_question", self.nodes.answer_question)
        workflow.add_node("summarize_content", self.nodes.summarize_content)
        workflow.add_node("handle_general_chat", self.nodes.handle_general_chat)
        workflow.add_node("redirect_to_time_agent", self.nodes.redirect_to_time_agent)
        workflow.add_node("finalize_response", self.nodes.finalize_response)

        # Set entry point
        workflow.set_entry_point("classify_intent")

        # Add conditional routing from classify_intent
        workflow.add_conditional_edges(
            "classify_intent",
            self._route_after_intent,
            {
                "retrieve_context": "retrieve_context",
                "general_chat": "handle_general_chat",
                "redirect": "redirect_to_time_agent",
            }
        )

        # Route from retrieve_context based on intent
        workflow.add_conditional_edges(
            "retrieve_context",
            self._route_after_context,
            {
                "quiz_generation": "generate_quiz",
                "question_answering": "answer_question",
                "content_summary": "summarize_content",
            }
        )

        # All processing nodes go to finalize
        workflow.add_edge("generate_quiz", "finalize_response")
        workflow.add_edge("answer_question", "finalize_response")
        workflow.add_edge("summarize_content", "finalize_response")
        workflow.add_edge("redirect_to_time_agent", "finalize_response")
        workflow.add_edge("handle_general_chat", "finalize_response")

        # Finalize goes to END
        workflow.add_edge("finalize_response", END)

        # Compile the graph
        memory = MemorySaver()
        self.compiled_graph = workflow.compile(checkpointer=memory)
        self.graph = workflow

        logger.info("✅ Study Agent graph built successfully!")

    def _route_after_intent(self, state: StudyAgentState) -> Literal[
        "retrieve_context",
        "general_chat",
        "redirect"
    ]:
        """
        Conditional routing after intent classification

        Routes to context retrieval for most intents,
        general chat for casual conversation,
        or redirect for Time Agent intents.
        """
        intent = state.get('intent', 'general_chat')

        logger.info(f"🔀 Routing based on intent: {intent}")

        if intent == "general_chat":
            return "general_chat"
        elif intent == "redirect_to_time_agent":
            return "redirect"
        else:
            return "retrieve_context"

    def _route_after_context(self, state: StudyAgentState) -> Literal[
        "quiz_generation",
        "question_answering",
        "content_summary"
    ]:
        """
        Conditional routing after context retrieval

        Routes to the appropriate processing node based on classified intent.
        """
        intent = state.get('intent', 'question_answering')

        logger.info(f"🔀 Routing to processing node: {intent}")

        # Map intent to node (Time Agent intents removed)
        routing_map = {
            "quiz_generation": "quiz_generation",
            "question_answering": "question_answering",
            "content_summary": "content_summary",
            "file_upload": "content_summary",  # Treat file upload as summary request
        }

        return routing_map.get(intent, "question_answering")

    def invoke(
        self,
        user_message: str,
        user_id: int = None,
        session_id: str = None,
        config: Dict[str, Any] = None
    ) -> StudyAgentState:
        """
        Invoke the Study Agent with a user message

        Args:
            user_message: User's input message in Macedonian
            user_id: Optional user/student ID
            session_id: Optional session identifier for state persistence
            config: Optional LangGraph configuration

        Returns:
            Final state with agent's response
        """
        logger.info(f"🚀 Invoking Study Agent with message: {user_message[:50]}...")

        try:
            # Create initial state
            initial_state = create_initial_state(
                user_message=user_message,
                user_id=user_id,
                session_id=session_id
            )

            # Configure graph execution
            if config is None:
                config = {
                    "configurable": {
                        "thread_id": session_id or "default"
                    }
                }

            # Invoke the graph
            final_state = self.compiled_graph.invoke(initial_state, config)

            logger.info(f"✅ Agent execution completed. Response: {final_state.get('response', '')[:50]}...")

            return final_state

        except Exception as e:
            logger.error(f"❌ Error in agent invocation: {e}")
            return StudyAgentState(
                user_message=user_message,
                error=str(e),
                error_type="agent_invocation_error",
                response="Жалам, имаше проблем при обработката на вашето барање.",
                should_end=True
            )

    def stream(
        self,
        user_message: str,
        user_id: int = None,
        session_id: str = None,
        config: Dict[str, Any] = None
    ):
        """
        Stream the Study Agent execution step by step

        Args:
            user_message: User's input message
            user_id: Optional user ID
            session_id: Optional session ID
            config: Optional configuration

        Yields:
            State updates as they occur
        """
        logger.info(f"🌊 Streaming Study Agent execution...")

        try:
            # Create initial state
            initial_state = create_initial_state(
                user_message=user_message,
                user_id=user_id,
                session_id=session_id
            )

            # Configure graph execution
            if config is None:
                config = {
                    "configurable": {
                        "thread_id": session_id or "default"
                    }
                }

            # Stream execution
            for event in self.compiled_graph.stream(initial_state, config):
                yield event

        except Exception as e:
            logger.error(f"❌ Error in agent streaming: {e}")
            yield {
                "error": StudyAgentState(
                    error=str(e),
                    error_type="streaming_error",
                    response="Грешка при streaming.",
                    should_end=True
                )
            }

    def get_graph_structure(self) -> str:
        """
        Get a string representation of the graph structure

        Returns:
            Graph structure description
        """
        if not self.compiled_graph:
            return "Graph not compiled"

        try:
            # Get graph structure
            return str(self.compiled_graph.get_graph())
        except Exception as e:
            logger.error(f"Error getting graph structure: {e}")
            return f"Error: {e}"

    def visualize_graph(self, output_path: str = "study_agent_graph.png"):
        """
        Visualize the graph structure (requires graphviz)

        Args:
            output_path: Path to save the visualization
        """
        try:
            from IPython.display import Image, display

            # Get graph
            graph = self.compiled_graph.get_graph()

            # Draw graph
            png_data = graph.draw_mermaid_png()

            # Save to file
            with open(output_path, 'wb') as f:
                f.write(png_data)

            logger.info(f"✅ Graph visualization saved to {output_path}")

            return Image(png_data)

        except Exception as e:
            logger.error(f"❌ Error visualizing graph: {e}")
            logger.info("💡 To visualize, install: pip install pygraphviz")
            return None


def build_study_agent_graph() -> StudyAgent:
    """
    Build and return a Study Agent with compiled LangGraph

    This is the main entry point for creating a Study Agent instance.

    Returns:
        Configured StudyAgent with compiled graph

    Example:
        >>> agent = build_study_agent_graph()
        >>> result = agent.invoke("Креирај квиз за фотосинтеза")
        >>> print(result['response'])
    """
    logger.info("🏗️ Building Study Agent Graph...")
    agent = StudyAgent()
    logger.info("✅ Study Agent ready!")
    return agent


# Convenience function for quick testing
def quick_test(message: str = "Здраво!"):
    """Quick test function for development"""
    agent = build_study_agent_graph()
    result = agent.invoke(message)
    print(f"\n💬 User: {message}")
    print(f"🤖 Agent: {result.get('response', 'No response')}")
    print(f"📊 Intent: {result.get('intent', 'unknown')}")
    print(f"🔄 Steps: {', '.join(result.get('steps_taken', []))}")
    return result


if __name__ == "__main__":
    # Test the agent
    logging.basicConfig(level=logging.INFO)
    quick_test("Креирај квиз за фотосинтеза")

