from typing import Literal

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from app.domain.enums import MainIntent
from app.domain.state import ConversationState

from app.graph.nodes import (
    answer_node,
    classify_node,
    expert_node,
    finalize_lead_node,
    general_node,
    main_menu_node,
    navigation_node,
    qualification_node,
    rag_node,
)


def route_initial_message(
    state: ConversationState,
) -> Literal[
    "navigation",
    "classify",
    "answer",
]:
    """
    Decide whether the request is:

    - a deterministic UI action
    - a qualification answer
    - a new natural-language request
    """

    if state.pending_action:
        return "navigation"

    if state.current_field:
        return "answer"

    return "classify"


def route_after_classification(
    state: ConversationState,
) -> Literal[
    "qualification",
    "rag",
    "expert",
    "main_menu",
    "general",
]:
    if (
        state.intent
        == MainIntent.SERVICE_REQUEST
    ):
        return "qualification"

    if state.intent == MainIntent.QUESTION:
        return "rag"

    if (
        state.intent
        == MainIntent.TALK_TO_EXPERT
    ):
        return "expert"

    if (
        state.intent
        == MainIntent.UNSURE_HELP
    ):
        return "main_menu"

    return "general"


def route_after_qualification(
    state: ConversationState,
) -> Literal[
    "finalize_lead",
    "end",
]:
    if state.qualification_complete:
        return "finalize_lead"

    return "end"


def build_conversation_graph():

    graph = StateGraph(
        ConversationState
    )

    graph.add_node(
        "classify",
        classify_node,
    )

    graph.add_node(
        "answer",
        answer_node,
    )

    graph.add_node(
        "navigation",
        navigation_node,
    )

    graph.add_node(
        "qualification",
        qualification_node,
    )

    graph.add_node(
        "rag",
        rag_node,
    )

    graph.add_node(
        "expert",
        expert_node,
    )

    graph.add_node(
        "main_menu",
        main_menu_node,
    )

    graph.add_node(
        "general",
        general_node,
    )

    graph.add_node(
        "finalize_lead",
        finalize_lead_node,
    )


    # ---------------------------------------------------------
    # Entry routing
    # ---------------------------------------------------------

    graph.add_conditional_edges(
        START,
        route_initial_message,
        {
            "navigation": "navigation",
            "classify": "classify",
            "answer": "answer",
        },
    )


    # ---------------------------------------------------------
    # Classification routing
    # ---------------------------------------------------------

    graph.add_conditional_edges(
        "classify",
        route_after_classification,
        {
            "qualification":
                "qualification",

            "rag":
                "rag",

            "expert":
                "expert",

            "main_menu":
                "main_menu",

            "general":
                "general",
        },
    )


    # ---------------------------------------------------------
    # Qualification answer
    # ---------------------------------------------------------

    graph.add_edge(
        "answer",
        "qualification",
    )


    # ---------------------------------------------------------
    # Qualification completion
    # ---------------------------------------------------------

    graph.add_conditional_edges(
        "qualification",
        route_after_qualification,
        {
            "finalize_lead":
                "finalize_lead",

            "end":
                END,
        },
    )


    # ---------------------------------------------------------
    # Terminal nodes
    # ---------------------------------------------------------

    graph.add_edge(
        "navigation",
        END,
    )

    graph.add_edge(
        "rag",
        END,
    )

    graph.add_edge(
        "expert",
        END,
    )

    graph.add_edge(
        "main_menu",
        END,
    )

    graph.add_edge(
        "general",
        END,
    )

    graph.add_edge(
        "finalize_lead",
        END,
    )


    return graph.compile()


conversation_graph = (
    build_conversation_graph()
)