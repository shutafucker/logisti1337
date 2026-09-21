"""Safe AI interpretation for dispatcher messages.

The package is intentionally independent from the FastAPI application and its
database. The host app supplies the current plan and vehicle IDs at the router
boundary.
"""
