"""In-process message bus. Agents never call each other: they send Messages through here.

Every message (requests, replies, broadcasts) is written to agent_messages BEFORE delivery,
so one user action can be traced across agents by its conversation_id.
"""
