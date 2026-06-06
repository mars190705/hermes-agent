"""Dump the actual system prompt size as the gateway would build it."""
import sys, os
sys.path.insert(0, '/opt/hermes')

# Force the same env the gateway uses
os.environ.setdefault('HERMES_HOME', '/opt/data')

from agent.prompt_builder import (
    build_skills_system_prompt,
    clear_skills_system_prompt_cache,
)
clear_skills_system_prompt_cache()

# Skills section
skills = build_skills_system_prompt(set(), set())
print(f'skills section: {len(skills)} chars')

# Snapshot disk version too
import json
from pathlib import Path
snap = Path('/opt/data/.skills_prompt_snapshot.json')
if snap.exists():
    print(f'snapshot file: {snap.stat().st_size} bytes')
    # Inspect a couple skill entries
    data = json.loads(snap.read_text(encoding='utf-8'))
    sk = data.get('skills', [])
    print(f'snapshot has {len(sk)} skill entries')
    if sk:
        long_descs = sorted(sk, key=lambda e: -len(e.get('description', '')))[:3]
        for e in long_descs:
            d = e.get('description', '')
            print(f"  {e.get('skill_name')}: desc len={len(d)}")
