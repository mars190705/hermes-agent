"""Probe hermes's model metadata for context lengths."""
import sys
sys.path.insert(0, '/opt/hermes')

from agent.model_metadata import fetch_model_metadata

cache = fetch_model_metadata()
print(f"models cached: {len(cache)}")
print()
picks = [
    'minimax/minimax-m2.5:free',
    'google/gemma-4-31b-it:free',
    'openai/gpt-oss-120b:free',
    'anthropic/claude-sonnet-4.6',
    'deepseek/deepseek-v3.2',
]
for mid in picks:
    e = cache.get(mid, {})
    if not e:
        print(f"{mid}: NOT IN CACHE")
        continue
    ctx = e.get("context_length", "?")
    mc = e.get("max_completion_tokens", "?")
    print(f"{mid}: ctx={ctx} max_completion={mc}")
