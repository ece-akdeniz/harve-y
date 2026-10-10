"""Typed errors shared by the V2 domain boundary."""


class ContractViolation(ValueError):
    """A value violates a frozen V2 contract invariant."""
