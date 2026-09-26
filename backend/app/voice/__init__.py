"""Shared JARVIS voice state vocabulary."""
from enum import Enum

class VoiceState(str, Enum):
    IDLE="idle"; LISTENING="listening"; THINKING="thinking"; SPEAKING="speaking"; ERROR="error"

__all__=["VoiceState"]
