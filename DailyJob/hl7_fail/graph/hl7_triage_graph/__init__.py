"""LangGraph port of the hl7_file_input daily triage.

Deterministic nodes (DB query, classification, customer resolution, pricing
lookup) are plain Python; the only LLM node writes the narrative from facts
the graph already established. See README.md next to this package.
"""
