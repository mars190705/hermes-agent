"""Throwaway smoke-test for per-skill backend routing inside the gateway."""
import json, sys
sys.path.insert(0, '/opt/hermes')

from tools.skills_tool import skill_view
from tools import terminal_tool

terminal_tool._task_env_overrides.clear()
result = json.loads(skill_view('pptx'))
print('skill_view:', result.get('success'))

cfg = terminal_tool._get_env_config(None)
print('routed cwd=', cfg['cwd'], 'image=', cfg['docker_image'], 'network=', cfg['docker_network'])

cc = {
    'cpu': cfg['container_cpu'], 'memory': cfg['container_memory'], 'disk': cfg['container_disk'],
    'container_persistent': False,
    'docker_volumes': cfg['docker_volumes'],
    'docker_forward_env': cfg['docker_forward_env'],
    'docker_env': cfg['docker_env'],
    'docker_mount_cwd_to_workspace': False,
    'docker_run_as_host_user': False,
    'docker_network': cfg['docker_network'],
}
env = terminal_tool._create_environment(
    env_type='docker', image=cfg['docker_image'], cwd=cfg['cwd'],
    timeout=30, container_config=cc, task_id='smoke',
)
print('container=', env._container_id[:12])
r = env.execute('libreoffice --version', timeout=30)
print('libreoffice exit:', r.get('returncode'), 'out:', r.get('output', '').strip()[:120])
r = env.execute('python3 -c "import pptx; print(pptx.__version__)"', timeout=30)
print('python-pptx exit:', r.get('returncode'), 'out:', r.get('output', '').strip()[:120])
r = env.execute('which pandoc && pandoc --version | head -1', timeout=30)
print('pandoc exit:', r.get('returncode'), 'out:', r.get('output', '').strip()[:120])
env.cleanup()
