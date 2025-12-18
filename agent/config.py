"""
Configuration module for JEX voice agent.
Supports multiple LLM, STT, and TTS providers via environment variables.
"""

import os
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class STTProvider(Enum):
    DEEPGRAM = "deepgram"
    OPENAI = "openai"
    GOOGLE = "google"
    ASSEMBLYAI = "assemblyai"


class TTSProvider(Enum):
    OPENAI = "openai"
    ELEVENLABS = "elevenlabs"
    CARTESIA = "cartesia"
    GOOGLE = "google"


@dataclass
class LLMConfig:
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@dataclass
class STTConfig:
    provider: STTProvider
    model: Optional[str] = None
    api_key: Optional[str] = None


@dataclass
class TTSConfig:
    provider: TTSProvider
    voice: str
    api_key: Optional[str] = None


def get_llm_config() -> LLMConfig:
    """Load LLM configuration from environment variables."""
    provider_str = os.getenv("LLM_PROVIDER", "openai").lower()
    provider = LLMProvider(provider_str)

    return LLMConfig(
        provider=provider,
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY") if provider == LLMProvider.OPENAI else None,
        base_url=os.getenv("OLLAMA_BASE_URL") if provider == LLMProvider.OLLAMA else None,
    )


def get_stt_config() -> STTConfig:
    """Load STT configuration from environment variables."""
    provider_str = os.getenv("STT_PROVIDER", "deepgram").lower()
    provider = STTProvider(provider_str)

    return STTConfig(
        provider=provider,
        model=os.getenv("STT_MODEL", "nova-2"),
        api_key=os.getenv("DEEPGRAM_API_KEY") if provider == STTProvider.DEEPGRAM else None,
    )


def get_tts_config() -> TTSConfig:
    """Load TTS configuration from environment variables."""
    provider_str = os.getenv("TTS_PROVIDER", "openai").lower()
    provider = TTSProvider(provider_str)

    return TTSConfig(
        provider=provider,
        voice=os.getenv("TTS_VOICE", "alloy"),
        api_key=os.getenv("ELEVENLABS_API_KEY") if provider == TTSProvider.ELEVENLABS else None,
    )


def create_llm(config: LLMConfig):
    """Factory function to create LLM instance based on config."""
    match config.provider:
        case LLMProvider.OPENAI:
            from livekit.plugins import openai
            return openai.LLM(model=config.model)
        case LLMProvider.ANTHROPIC:
            from livekit.plugins import anthropic
            return anthropic.LLM(model=config.model)
        case LLMProvider.GOOGLE:
            from livekit.plugins import google
            return google.LLM(model=config.model)
        case LLMProvider.OLLAMA:
            from livekit.plugins import ollama
            return ollama.LLM(model=config.model, base_url=config.base_url)
        case _:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")


def create_stt(config: STTConfig):
    """Factory function to create STT instance based on config."""
    match config.provider:
        case STTProvider.DEEPGRAM:
            from livekit.plugins import deepgram
            return deepgram.STT(model=config.model)
        case STTProvider.OPENAI:
            from livekit.plugins import openai
            return openai.STT()
        case STTProvider.GOOGLE:
            from livekit.plugins import google
            return google.STT()
        case STTProvider.ASSEMBLYAI:
            from livekit.plugins import assemblyai
            return assemblyai.STT()
        case _:
            raise ValueError(f"Unsupported STT provider: {config.provider}")


def create_tts(config: TTSConfig):
    """Factory function to create TTS instance based on config."""
    match config.provider:
        case TTSProvider.OPENAI:
            from livekit.plugins import openai
            return openai.TTS(voice=config.voice)
        case TTSProvider.ELEVENLABS:
            from livekit.plugins import elevenlabs
            return elevenlabs.TTS(voice=config.voice)
        case TTSProvider.CARTESIA:
            from livekit.plugins import cartesia
            return cartesia.TTS(voice=config.voice)
        case TTSProvider.GOOGLE:
            from livekit.plugins import google
            return google.TTS(voice=config.voice)
        case _:
            raise ValueError(f"Unsupported TTS provider: {config.provider}")
