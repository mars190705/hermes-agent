"""Throwaway: print curated OpenRouter model list with pricing."""
import json

with open('/opt/data/models_dev_cache.json', encoding='utf-8') as f:
    data = json.load(f)

or_models = data.get('openrouter', {}).get('models', {})
print('total openrouter models:', len(or_models))

picks = [
    'anthropic/claude-opus-4.7',
    'anthropic/claude-sonnet-4.6',
    'anthropic/claude-sonnet-4.5',
    'google/gemini-2.5-pro',
    'google/gemini-2.5-flash',
    'openai/gpt-5',
    'openai/gpt-5-mini',
    'deepseek/deepseek-v4-pro',
    'deepseek/deepseek-v3.2',
    'deepseek/deepseek-chat-v3.1',
    'qwen/qwen3-max',
    'qwen/qwen3-235b-a22b-07-25',
    'moonshotai/kimi-k2.6',
    'moonshotai/kimi-k2-thinking',
    'x-ai/grok-4',
    'openai/gpt-oss-120b',
    'openai/gpt-oss-120b:free',
]

print()
print(f"{'model':<46} {'in':>7} {'out':>7} {'ctx':>10}")
print('-' * 75)
for pid in picks:
    m = or_models.get(pid)
    if not m:
        print(f"{pid:<46} (not in catalog)")
        continue
    c = m.get('cost', {}) or {}
    inp = c.get('input', '?')
    out = c.get('output', '?')
    ctx = m.get('limit', {}).get('context', '?')
    print(f"{pid:<46} {str(inp):>7} {str(out):>7} {str(ctx):>10}")
