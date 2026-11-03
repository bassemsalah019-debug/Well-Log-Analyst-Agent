# """Model Initialization File

# Configures the LLM model used throughout the course.

# Default: Anthropic claude-haiku-4-5 (fast, cheap, great for learning).

# ═══════════════════════════════════════════════════════════════════════════
#   ⚠  IMPORTANT: install the matching extra BEFORE swapping providers
# ═══════════════════════════════════════════════════════════════════════════

#   Provider              Install command              Already installed?
#   --------------------  ---------------------------  ---------------------
#   Anthropic (default)   -                            yes (default dep)
#   OpenAI                -                            yes (default dep)
#   Azure OpenAI          uv sync --extra azure        no - install first
#   AWS Bedrock           uv sync --extra bedrock      no - install first
#   Google Vertex/Gemini  uv sync --extra google       no - install first

# ═══════════════════════════════════════════════════════════════════════════

# To swap providers:
#   1. Run the install command above (if needed).
#   2. Comment out the active model line(s) below.
#   3. Uncomment the section for your desired provider.
#   4. Set the provider's env vars in `.env` (see notes inline).
# """

# import os  # noqa: F401  # used in commented-out model examples below
# from pathlib import Path

# from dotenv import load_dotenv

# load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

# from langchain.chat_models import init_chat_model

# # ═══ Default Models ══════════════════════════════════════════════════════════
# # Workshop default: Anthropic claude-haiku-4-5, fast and cost-effective.
# # Requires ANTHROPIC_API_KEY in .env
# # model = init_chat_model("anthropic:claude-haiku-4-5", timeout=60, max_retries=2)
# model = init_chat_model("google_genai:gemini-flash-lite-latest", timeout=120, max_retries=2)
# #model = init_chat_model("groq:openai/gpt-oss-120b")


# #A more capable model for steps that need stronger reasoning
# # strong_model = init_chat_model("anthropic:claude-sonnet-5-5", timeout=120, max_retries=2)
# strong_model = init_chat_model("google_genai:gemini-flash-lite-latest", timeout=120, max_retries=2)
# # strong_model = init_chat_model("groq:openai/gpt-oss-120b")
# # ═══ Alternative Models (comment out default above, uncomment one below) ═════
# # model = init_chat_model("anthropic:claude-sonnet-5-5")
# # model = init_chat_model("openai:gpt-6-luna")
# # strong_model = init_chat_model("openai:gpt-6.1-sol")

# # ═══ Open-Source / Alternative Hosted Models ══════════════════════════════════

# # Groq: fast hosted inference for Llama, Mixtral, and others (free tier available)
# # Install first:  uv add langchain-groq
# # Requires GROQ_API_KEY in .env  (get one at console.groq.com)
# #
# # model = init_chat_model("groq:llama-3.3-70b-versatile")

# # Ollama: run models locally (no API key required)
# # langchain-ollama is already installed (default dep)
# # Install the Ollama app first: https://ollama.com
# # Pull a model first, e.g.:  ollama pull qwen2.5:7b
# # Note: small local models (7-8B) can mis-call tools or guess names; keep strong_model on a hosted model.
# #
# # model = init_chat_model("ollama:qwen2.5:7b")

# # Kimi (Moonshot AI): OpenAI-compatible hosted API
# # No extra install needed (langchain-openai is already a default dep)
# # Requires KIMI_API_KEY in .env  (get one at platform.moonshot.cn)
# #
# # from langchain_openai import ChatOpenAI
# # model = ChatOpenAI(model="moonshot-v1-8k", base_url="https://api.moonshot.cn/v1", api_key=os.environ["KIMI_API_KEY"])

# # OpenRouter: hosted open-source models via OpenAI-compatible API
# # No extra install needed (langchain-openai is already a default dep)
# # Free models available; sign up at openrouter.ai and get an API key
# # Requires OPENROUTER_API_KEY in .env
# #
# # from langchain_openai import ChatOpenAI
# # model = ChatOpenAI(model="nvidia/nemotron-3-ultra-550b-a55b:free", base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])


# # ═══ Cloud Provider Models (extra install required, see table above) ═════════
# # ─── Azure OpenAI ─────────────────────────────────────────────────────────────
# # Install first:  uv sync --extra azure
# # Requires AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, OPENAI_API_VERSION in .env
# # Set your deployment name directly below (it isn't read from .env)
# #
# # from langchain_openai import AzureChatOpenAI
# # model = AzureChatOpenAI(azure_deployment="gpt-4.1", api_version="2024-12-01-preview")


# # ─── AWS Bedrock ──────────────────────────────────────────────────────────────
# # Install first:  uv sync --extra bedrock
# # Requires AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY in .env
# # Set your region directly below (it isn't read from .env)
# #
# # from langchain_aws import ChatBedrockConverse
# # model = ChatBedrockConverse(model_id="anthropic.claude-sonnet-4-6", region_name="us-east-1")


# # ─── Google Gemini ────────────────────────────────────────────────────────────
# # Install first:  uv sync --extra google
# # Requires GOOGLE_API_KEY in .env
# #
# # model = init_chat_model("google_genai:gemini-3.8-flash")





"""Model Initialization File

Configures the LLM model used throughout the course.

Default: Anthropic claude-haiku-4-5 (fast, cheap, great for learning).

═══════════════════════════════════════════════════════════════════════════
  ⚠  IMPORTANT: install the matching extra BEFORE swapping providers
═══════════════════════════════════════════════════════════════════════════

  Provider              Install command              Already installed?
  --------------------  ---------------------------  ---------------------
  Anthropic (default)   -                            yes (default dep)
  OpenAI                -                            yes (default dep)
  Azure OpenAI          uv sync --extra azure        no - install first
  AWS Bedrock           uv sync --extra bedrock      no - install first
  Google Vertex/Gemini  uv sync --extra google       no - install first

═══════════════════════════════════════════════════════════════════════════

To swap providers:
  1. Run the install command above (if needed).
  2. Comment out the active model line(s) below.
  3. Uncomment the section for your desired provider.
  4. Set the provider's env vars in `.env` (see notes inline).
"""

import os  # noqa: F401  # used in commented-out model examples below
from functools import cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

from langchain.chat_models import init_chat_model

# ═══ Default Models ══════════════════════════════════════════════════════════
# Each model is built the first time it is used, not at import time, so the
# no-LLM checks (test_petrophysics.py, agent.py --check) run without an API key.
# Workshop default: Anthropic claude-haiku-4-5, fast and cost-effective.
# Requires ANTHROPIC_API_KEY in .env
@cache
def get_model():
    # return init_chat_model("anthropic:claude-haiku-4-5", timeout=60, max_retries=2)
    return init_chat_model("google_genai:gemini-flash-lite-latest", timeout=120, max_retries=2)
    # return init_chat_model("groq:openai/gpt-oss-120b")   # Groq: back when the daily limit resets


# A lighter model for the well-analyst subagent (Lesson 4.2)
@cache
def get_light_model():
    return init_chat_model("google_genai:gemini-flash-lite-latest", timeout=120, max_retries=2)
    # return init_chat_model("groq:openai/gpt-oss-20b")


#A more capable model for steps that need stronger reasoning
@cache
def get_strong_model():
    # return init_chat_model("anthropic:claude-sonnet-5-5", timeout=120, max_retries=2)
    return init_chat_model("google_genai:gemini-flash-lite-latest", timeout=120, max_retries=2)
    # return init_chat_model("groq:openai/gpt-oss-120b")


_LAZY_MODELS = {"model": get_model, "light_model": get_light_model, "strong_model": get_strong_model}


def __getattr__(name):
    """`from models import model` still works: the model is built here, on first use (PEP 562)."""
    if name in _LAZY_MODELS:
        return _LAZY_MODELS[name]()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ═══ Alternative Models (comment out default above, uncomment one below) ═════
# model = init_chat_model("anthropic:claude-sonnet-5-5")
# model = init_chat_model("openai:gpt-6-luna")
# strong_model = init_chat_model("openai:gpt-6.1-sol")

# ═══ Open-Source / Alternative Hosted Models ══════════════════════════════════

# Groq: fast hosted inference for Llama, Mixtral, and others (free tier available)
# Install first:  uv add langchain-groq
# Requires GROQ_API_KEY in .env  (get one at console.groq.com)
#
# model = init_chat_model("groq:llama-3.3-70b-versatile")

# Ollama: run models locally (no API key required)
# langchain-ollama is already installed (default dep)
# Install the Ollama app first: https://ollama.com
# Pull a model first, e.g.:  ollama pull qwen2.5:7b
# Note: small local models (7-8B) can mis-call tools or guess names; keep strong_model on a hosted model.
#
# model = init_chat_model("ollama:qwen2.5:7b")

# Kimi (Moonshot AI): OpenAI-compatible hosted API
# No extra install needed (langchain-openai is already a default dep)
# Requires KIMI_API_KEY in .env  (get one at platform.moonshot.cn)
#
# from langchain_openai import ChatOpenAI
# model = ChatOpenAI(model="moonshot-v1-8k", base_url="https://api.moonshot.cn/v1", api_key=os.environ["KIMI_API_KEY"])

# OpenRouter: hosted open-source models via OpenAI-compatible API
# No extra install needed (langchain-openai is already a default dep)
# Free models available; sign up at openrouter.ai and get an API key
# Requires OPENROUTER_API_KEY in .env
#
# from langchain_openai import ChatOpenAI
# model = ChatOpenAI(model="nvidia/nemotron-3-ultra-550b-a55b:free", base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])


# ═══ Cloud Provider Models (extra install required, see table above) ═════════
# ─── Azure OpenAI ─────────────────────────────────────────────────────────────
# Install first:  uv sync --extra azure
# Requires AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, OPENAI_API_VERSION in .env
# Set your deployment name directly below (it isn't read from .env)
#
# from langchain_openai import AzureChatOpenAI
# model = AzureChatOpenAI(azure_deployment="gpt-4.1", api_version="2024-12-01-preview")


# ─── AWS Bedrock ──────────────────────────────────────────────────────────────
# Install first:  uv sync --extra bedrock
# Requires AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY in .env
# Set your region directly below (it isn't read from .env)
#
# from langchain_aws import ChatBedrockConverse
# model = ChatBedrockConverse(model_id="anthropic.claude-sonnet-4-6", region_name="us-east-1")


# ─── Google Gemini ────────────────────────────────────────────────────────────
# Install first:  uv sync --extra google
# Requires GOOGLE_API_KEY in .env
#
# model = init_chat_model("google_genai:gemini-3.8-flash")
