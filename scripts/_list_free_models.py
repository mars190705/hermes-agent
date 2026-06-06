"""List all free OpenRouter models with relevant attributes."""
import json

with open('/opt/data/models_dev_cache.json', encoding='utf-8') as f:
    data = json.load(f)

or_models = data.get('openrouter', {}).get('models', {})
free = []
for mid, m in or_models.items():
    if not mid.endswith(':free'):
        continue
    c = m.get('cost', {}) or {}
    # All ":free" entries should have 0/0, but double-check
    if (c.get('input') or 0) == 0 and (c.get('output') or 0) == 0:
        free.append((mid, m))

free.sort(key=lambda x: x[0])
print(f"total free models: {len(free)}")
print()
print(f"{'model':<55} {'ctx':>10} {'tools':>6} {'reasoning':>10}")
print('-' * 90)
for mid, m in free:
    ctx = m.get('limit', {}).get('context', '?')
    tools = m.get('tool_call', False)
    reasoning = m.get('reasoning', False)
    print(f"{mid:<55} {str(ctx):>10} {str(tools):>6} {str(reasoning):>10}")
