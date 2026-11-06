#!/usr/bin/env python3
"""Named native Hermes workers in Herdr; no credential handling or DB writes."""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parent
HERDR = ROOT / 'herdr-trial'
HOME = Path.home() / '.hermes'
RUNTIME = ROOT / 'runtime'
NAME = re.compile(r'[a-z][a-z0-9_-]{0,23}\Z')
TOOLS = ['terminal', 'file', 'skills', 'memory', 'session_search']


def validate_name(name):
    if not NAME.fullmatch(name):
        raise ValueError('Use a lowercase name, max24 characters, letters/digits/_/-.')
    return name


def run(args, timeout=40):
    p = subprocess.run([str(HERDR), *args], text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout).strip()[:1600])
    return json.loads(p.stdout)


def save_records(data):
    path = RUNTIME / 'workers.json'
    temp = RUNTIME / ('workers.' + uuid.uuid4().hex + '.json')
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump(data, out, indent=2)
        out.flush()
        os.fsync(out.fileno())
    os.replace(temp, path)


@contextlib.contextmanager
def records():
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    RUNTIME.chmod(0o700)
    lock = RUNTIME / 'workers.lock'
    fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        path = RUNTIME / 'workers.json'
        data = json.loads(path.read_text()) if path.exists() else {}
        yield data
        save_records(data)


def native_session(title):
    """Read only the exact worker's native ID; never edit Hermes session data."""
    path = HOME / 'state.db'
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=3) as c:
        rows = c.execute('SELECT id FROM sessions WHERE title=? ORDER BY started_at DESC LIMIT 2', (title,)).fetchall()
    if len(rows) > 1:
        raise RuntimeError('Ambiguous native session title; refusing guessed association.')
    return rows[0][0] if rows else None


def local_memory_preflight():
    """Fail closed if this workflow would silently lose or move memory."""
    from urllib.parse import urlparse
    import ipaddress
    import yaml
    if os.getenv('HERMES_HOME') and Path(os.environ['HERMES_HOME']).resolve() != HOME.resolve():
        raise RuntimeError('Managed workers require default Hermes home; no cross-profile launch.')
    for flag in ('HERMES_SAFE_MODE', 'HERMES_IGNORE_USER_CONFIG', 'HERMES_IGNORE_RULES'):
        if os.getenv(flag, '').lower() in ('1', 'true', 'yes', 'on'):
            raise RuntimeError('Bypass environment would disable shared worker memory: ' + flag)
    config = yaml.safe_load((HOME / 'config.yaml').read_text()) or {}
    memory = config.get('memory') or {}
    if memory.get('provider') != 'honcho' or 'honcho' not in (config.get('plugins') or {}).get('enabled', []):
        raise RuntimeError('Existing Honcho memory provider/plugin must be enabled; no fallback.')
    h = json.loads((HOME / 'honcho.json').read_text())['hosts']['hermes']
    parsed = urlparse(h.get('baseUrl', ''))
    try:
        local = parsed.hostname == 'localhost' or ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        local = False
    if not local or parsed.scheme not in ('http', 'https') or h.get('enabled') is not True or parsed.username or parsed.password:
        raise RuntimeError('Enabled LOCAL Honcho endpoint required; no cloud fallback.')
    import http.client
    connection = (http.client.HTTPSConnection if parsed.scheme == 'https' else http.client.HTTPConnection)(parsed.hostname, parsed.port, timeout=5)
    try:
        connection.request('GET', (parsed.path.rstrip('/') or '') + '/health')
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError('Local Honcho health is unavailable; worker not launched.')
        response.read(4096)
    finally:
        connection.close()
    return {'endpoint': h['baseUrl'], 'workspace': h.get('workspace'),
            'mode': 'native shared memory; inference health must be reported separately'}


def route():
    """Reuse the operator's configured native delegation route; no API secrets."""
    import yaml
    config = yaml.safe_load((HOME / 'config.yaml').read_text()) or {}
    d = config.get('delegation') or {}
    provider, model = d.get('provider'), d.get('model')
    if not isinstance(provider, str) or not isinstance(model, str) or not provider or not model:
        raise RuntimeError('Configured delegation provider/model required; no implicit fallback.')
    return provider, model


def argv(session_id, prompt_path):
    # The native gateway owns creation policy; attach without conflicting
    # creation flags. This also avoids CLI --continue's two-stage route trap.
    return ['chat', '--cli', '--resume', session_id, '--query-file', str(prompt_path)]


def create_native_session(title, cwd, turns, provider, model, request_id):
    """Use the same authenticated local gateway API as Desktop/native CLI."""
    import asyncio
    import sys
    sys.path.insert(0, str(HOME / 'hermes-agent'))
    from hermes_cli.gateway_client import connect_gateway

    async def create():
        async with connect_gateway() as client:
            description = await client.rpc('runtime.describe')
            parameters = {'request_id': request_id, 'source': 'cli', 'title': title,
                          'cwd': str(cwd), 'provider': provider, 'model': model,
                          'toolsets': TOOLS, 'max_turns': turns, 'safe_mode': False,
                          'ignore_user_config': False, 'ignore_rules': False, 'yolo': False}
            if set(parameters) - set(description['session_create']['parameters']):
                raise RuntimeError('Native gateway contract does not support worker creation policy.')
            snapshot = await client.rpc('session.create', **parameters)
            info = snapshot.get('info') or {}
            if info.get('model') != model:
                raise RuntimeError('Native session model differs from requested route; no prompt submitted.')
            return snapshot['stored_session_id']
    return asyncio.run(asyncio.wait_for(create(), timeout=30))


def ensure_server():
    """Start only the dedicated user-local Herdr server, never the Hermes gateway."""
    p = subprocess.run([str(HERDR), 'status'], text=True, capture_output=True, timeout=10)
    if p.returncode:
        raise RuntimeError('Cannot inspect dedicated Herdr server; refusing automatic replacement.')
    if 'status: running' in p.stdout:
        if 'endpoint_compatible: yes' not in p.stdout:
            raise RuntimeError('Existing Herdr server incompatible; no automatic upgrade/restart.')
        return
    if 'status: not running' not in p.stdout:
        raise RuntimeError('Unknown Herdr status; refusing duplicate server.')
    env = {k: os.environ[k] for k in ('HOME', 'PATH', 'LANG', 'XDG_RUNTIME_DIR') if k in os.environ}
    env.update({'SHELL': '/bin/sh', 'TERM': 'xterm-256color'})
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(RUNTIME / 'managed-server.log', os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'a') as output:
        subprocess.Popen([str(HERDR), 'server'], env=env, cwd=ROOT,
                         stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                         start_new_session=True)
    for _ in range(20):
        time.sleep(0.25)
        p = subprocess.run([str(HERDR), 'status'], text=True, capture_output=True, timeout=5)
        if p.returncode == 0 and 'status: running' in p.stdout:
            return
    raise RuntimeError('Dedicated Herdr startup unverified; inspect managed-server.log.')


def start(name, cwd, prompt, turns=20):
    validate_name(name)
    cwd = Path(cwd).expanduser().resolve(strict=True)
    if not cwd.is_dir() or not prompt.strip() or len(prompt.encode()) > 32000:
        raise ValueError('Existing cwd and nonempty prompt <=32000 bytes required.')
    if not 1 <= turns <= 40:
        raise ValueError('max-turns must be within1..40.')
    provider, model = route()
    with records() as data:
        if name in data:
            # Idempotent: a repeated request never submits the prompt again.
            return describe(data[name])
        memory = local_memory_preflight()
        ensure_server()
        live = run(['agent', 'list'])['result']['agents']
        if sum(a.get('name', '').startswith('hw-') for a in live) >= 2:
            raise RuntimeError('Two managed workers already active; inspect/stop one first.')
        if any(a.get('name') == 'hw-' + name for a in live):
            raise RuntimeError('Untracked worker name already live; inspect rather than resubmit.')
        prompt_path = RUNTIME / (name + '.prompt.txt')
        if prompt_path.exists():
            raise RuntimeError('Prior prompt admission may exist; inspect rather than resubmit.')
        created = run(['workspace', 'create', '--cwd', str(cwd), '--label', 'Herdr: ' + name, '--no-focus'])['result']
        pane = created['root_pane']['pane_id']
        title = '[Herdr] ' + name + ' ' + uuid.uuid4().hex[:8]
        prompt_path = RUNTIME / (name + '.prompt.txt')
        fd = os.open(prompt_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(prompt)
        rec = {'name': name, 'agent_name': 'hw-' + name, 'pane_id': pane,
               'workspace_id': created['workspace']['workspace_id'], 'title': title,
               'cwd': str(cwd), 'provider': provider, 'model': model, 'honcho': memory,
               'created_at': time.time(), 'launch_status': 'created', 'request_id': uuid.uuid4().hex}
        data[name] = rec
        save_records(data)  # durable identity before gateway creation/admission
        # Retain ambiguous admission rather than retrying a possibly running prompt.
        try:
            rec['session_id'] = create_native_session(title, cwd, turns, provider, model, rec['request_id'])
            save_records(data)  # native conversation known before submitting text
            run(['agent', 'start', rec['agent_name'], '--kind', 'hermes', '--pane', pane,
                 '--timeout', '25000', '--', *argv(rec['session_id'], prompt_path)], timeout=35)
            rec['launch_status'] = 'started'
        except Exception as e:
            rec['launch_status'] = 'inspect_required'
            rec['launch_error'] = type(e).__name__ + ': ' + str(e)[:1500]
        data[name] = rec
        return describe(rec)


def describe(rec):
    result = dict(rec)
    try:
        result['session_id'] = rec.get('session_id') or native_session(rec['title'])
    except (OSError, sqlite3.Error, RuntimeError) as e:
        result['session_lookup_error'] = type(e).__name__
    result['note'] = 'Herdr badges are advisory. Read the native conversation; do not retry ambiguous admission.'
    return result


def settled(snapshot, prompt):
    users = [m for m in snapshot.get('messages',[]) if m.get('role')=='user']
    seen = bool(users and str(users[-1].get('content','')).strip() == prompt.strip())
    tail = (snapshot.get('messages') or [{}])[-1]
    return bool(seen and not snapshot.get('running') and not snapshot.get('pending')
                and not snapshot.get('prompts') and tail.get('role')=='assistant'
                and not tail.get('tool_calls'))


def wait_worker(rec, timeout=600):
    """Wait for native turn settlement, never a Herdr badge or a task-quality verdict."""
    import asyncio
    import sys
    sys.path.insert(0, str(HOME / 'hermes-agent'))
    from hermes_cli.gateway_client import connect_gateway
    sid = rec.get('session_id') or native_session(rec['title'])
    prompt = (RUNTIME / (rec['name'] + '.prompt.txt')).read_text().strip()

    async def wait():
        deadline = time.monotonic()+timeout
        async with connect_gateway() as client:
            while time.monotonic()<deadline:
                snapshot = await client.rpc('session.resume', session_id=sid)
                messages = snapshot.get('messages') or []
                tail = messages[-1] if messages else {}
                if snapshot.get('prompts'):
                    return {'status':'needs_input','session_id':sid,'title':rec['title'],
                            'note':'Inspect the native approval/question; do not auto-answer.'}
                if settled(snapshot, prompt):
                    return {'status':'turn_settled','session_id':sid,'title':rec['title'],
                            'result_excerpt':str(tail.get('content',''))[-4000:],
                            'note':'Parent must verify artifacts/tests; this is not task-quality approval.'}
                await asyncio.sleep(2)
        return {'status':'still_pending','session_id':sid,'title':rec['title'],
                'note':'Conversation remains durable; do not replay the task.'}
    return asyncio.run(asyncio.wait_for(wait(), timeout=timeout+15))


def stop_native(rec):
    """Closing a terminal alone does not cancel a gateway-owned model run."""
    import asyncio
    import sys
    sys.path.insert(0, str(HOME / 'hermes-agent'))
    from hermes_cli.gateway_client import connect_gateway

    async def stop():
        sid = rec.get('session_id') or native_session(rec['title'])
        if not sid:
            return {'running': False, 'native_session': None}
        async with connect_gateway() as client:
            snapshot = await client.rpc('session.resume', session_id=sid)
            if snapshot.get('running'):
                await client.rpc('session.interrupt', session_id=sid,
                                 execution_generation=snapshot['execution_generation'])
                for _ in range(20):
                    snapshot = await client.rpc('session.resume', session_id=sid)
                    if not snapshot.get('running'):
                        break
                    await asyncio.sleep(0.25)
            if snapshot.get('running') or snapshot.get('pending'):
                raise RuntimeError('Native run or queued work remains; terminal left open for inspection.')
            return {'running': False, 'native_session': sid}
    return asyncio.run(asyncio.wait_for(stop(), timeout=15))


def resume_worker(rec):
    local_memory_preflight()
    ensure_server()
    live = run(['agent', 'list'])['result']['agents']
    if any(a.get('name') == rec['agent_name'] for a in live):
        return describe(rec)
    if sum(a.get('name', '').startswith('hw-') for a in live) >= 2:
        raise RuntimeError('Two managed workers already active.')
    sid = rec.get('session_id') or native_session(rec['title'])
    if not sid:
        raise RuntimeError('No known native conversation to resume; no new prompt submitted.')
    created = run(['workspace', 'create', '--cwd', rec['cwd'], '--label', 'Herdr: ' + rec['name'], '--no-focus'])['result']
    rec.update(pane_id=created['root_pane']['pane_id'], workspace_id=created['workspace']['workspace_id'], session_id=sid)
    try:
        run(['agent', 'start', rec['agent_name'], '--kind', 'hermes', '--pane', rec['pane_id'],
             '--timeout', '25000', '--', 'chat', '--cli', '--resume', sid], timeout=35)
        rec['launch_status'] = 'resumed'
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        rec['launch_status'] = 'inspect_required'
        rec['launch_error'] = str(e)[:1600]
    return describe(rec)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    s = sub.add_parser('start')
    s.add_argument('--name', required=True)
    s.add_argument('--cwd', required=True)
    s.add_argument('--prompt-file', required=True)
    s.add_argument('--max-turns', type=int, default=20)
    sub.add_parser('list')
    for action in ('show', 'read', 'stop', 'resume', 'wait'):
        q = sub.add_parser(action)
        q.add_argument('name')
        if action == 'wait':
            q.add_argument('--timeout', type=int, default=600)
    args = p.parse_args()
    if args.action == 'wait':
        if not 1 <= args.timeout <= 3600:
            raise ValueError('wait timeout must be within1..3600 seconds.')
        with records() as data:
            rec = dict(data[validate_name(args.name)])
        print(json.dumps(wait_worker(rec, args.timeout), indent=2))
        return
    if args.action == 'start':
        result = start(args.name, args.cwd, Path(args.prompt_file).read_text(), args.max_turns)
    else:
        with records() as data:
            if args.action == 'list':
                result = [describe(rec) for rec in data.values()]
            else:
                rec = data[validate_name(args.name)]
                result = describe(rec)
                if args.action == 'resume':
                    result = resume_worker(rec)
                if args.action == 'read':
                    sid = result.get('session_id')
                    if not sid:
                        raise RuntimeError('Native session not yet found; inspect pane, do not resubmit.')
                    # Supported native export, scoped to one owned record; no upload.
                    done = subprocess.run(['hermes', 'sessions', 'export', '-', '--session-id', sid,
                                           '--redact', '--format', 'jsonl', '--yes'], check=True)
                    return
                if args.action == 'stop':
                    # Only close a pane created/tracked by this launcher.
                    result['native_stop'] = stop_native(rec)
                    result['close_result'] = run(['pane', 'close', rec['pane_id']])
                    rec['launch_status'] = 'pane_closed'
                    result['launch_status'] = 'pane_closed'
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, KeyError, OSError, subprocess.SubprocessError) as e:
        print(json.dumps({'error': str(e)[:1600]}))
        raise SystemExit(1)
