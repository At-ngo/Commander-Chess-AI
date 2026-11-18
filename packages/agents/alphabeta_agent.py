"""Compatibility alias for alpha_beta_agent."""
try:
    from packages.agents.alpha_beta_agent import AlphaBetaAgent
except ModuleNotFoundError:
    from agents.alpha_beta_agent import AlphaBetaAgent

__all__ = ["AlphaBetaAgent"]
