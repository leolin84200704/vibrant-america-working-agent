"""Graph wiring.

START -> preflight -+-> fetch_failed -+-> classify -> resolve_customer -> lookup_codes -> write_report -> send_mail -> END
                    |                 '-> write_report (no records) ------------------------^
                    '-> write_blocked_report -> send_mail -> END
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from . import nodes
from .state import TriageState


def build_graph():
    builder = StateGraph(TriageState)
    builder.add_node("preflight", nodes.preflight)
    builder.add_node("fetch_failed", nodes.fetch_failed)
    builder.add_node("classify", nodes.classify)
    builder.add_node("resolve_customer", nodes.resolve_customer)
    builder.add_node("lookup_codes", nodes.lookup_codes)
    builder.add_node("write_report", nodes.write_report)
    builder.add_node("write_blocked_report", nodes.write_blocked_report)
    builder.add_node("send_mail", nodes.send_mail)

    builder.add_edge(START, "preflight")
    builder.add_conditional_edges("preflight", nodes.route_after_preflight,
                                  ["fetch_failed", "write_blocked_report"])
    builder.add_conditional_edges("fetch_failed", nodes.route_after_fetch, ["classify", "write_report"])
    builder.add_edge("classify", "resolve_customer")
    builder.add_edge("resolve_customer", "lookup_codes")
    builder.add_edge("lookup_codes", "write_report")
    builder.add_edge("write_report", "send_mail")
    builder.add_edge("write_blocked_report", "send_mail")
    builder.add_edge("send_mail", END)
    return builder.compile()


graph = build_graph()
