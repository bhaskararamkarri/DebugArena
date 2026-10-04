"""Probe Docker sandbox environment and network isolation."""
import docker

client = docker.from_env()
cmd = """
echo "=== UNAME ==="
uname -a
echo "=== PYTHON ==="
python3 --version
echo "=== WHOAMI ==="
whoami
echo "=== NETWORK PROBE ==="
python3 -c "import urllib.request as u; u.urlopen('https://example.com', timeout=3)"
"""

container = client.containers.run(
    "agentgym-sandbox:python3.11",
    command=["/bin/sh", "-c", cmd],
    network_disabled=True,
    mem_limit="256m",
    nano_cpus=int(0.5 * 1e9),
    pids_limit=128,
    detach=True,
)

res = container.wait()
logs = container.logs().decode(errors="replace")
container.remove(force=True)

print(f"Exit code: {res.get('StatusCode')}")
print(logs)
