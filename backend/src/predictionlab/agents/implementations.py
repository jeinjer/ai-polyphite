"""Versioned logical agents; inference details remain behind ModelBackend."""

from predictionlab.agents.base import BackendPredictionAgent


class ReasoningAgent(BackendPredictionAgent):
    name = "reasoning"
    version = "1.0.0"


class MarketAgent(BackendPredictionAgent):
    name = "market"
    version = "1.0.0"


class SkepticAgent(BackendPredictionAgent):
    name = "skeptic"
    version = "1.0.0"


class ConsensusAgent(BackendPredictionAgent):
    name = "consensus"
    version = "2.0.0"
