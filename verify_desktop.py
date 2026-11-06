#!/usr/bin/env python3
"""Read-only, scoped checks against the existing authenticated Desktop backend."""
import argparse
import json
from pathlib import Path
import sys
import urllib.request
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(Path.home()/'.hermes/hermes-agent'))
from hermes_constants import get_hermes_home
from hermes_cli.gateway_runtime import discover_gateway_endpoint
from hermes_cli.gateway_client import _session_ticket


def verify(base, names):
    parsed = urlparse(base)
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1':
        raise ValueError('Use the existing loopback Desktop backend only.')
    home = get_hermes_home().resolve()
    endpoint = discover_gateway_endpoint(home).endpoint
    records = json.loads((ROOT/'runtime/workers.json').read_text())

    def get(path):
        # Tickets are short-lived native HTTP grants, not copied OAuth secrets.
        # Each request redeems its own ticket; do not print/persist it.
        ticket = _session_ticket(home, endpoint, purpose='native-http')
        request = urllib.request.Request(base+path, headers={'x-hermes-gateway-ticket':ticket})
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)

    listing = get('/api/profiles/sessions/sidebar?recents_profile=default&recents_limit=50&cron_limit=1&messaging_limit=1&recents_exclude=acp,cron,kanban,oneshot,subagent,tool')['recents']
    def rows(x):
        if isinstance(x, dict):
            if 'id' in x and 'title' in x:
                yield x
            else:
                for value in x.values():yield from rows(value)
        elif isinstance(x,list):
            for value in x:yield from rows(value)
    visible = {r['id']:r for r in rows(listing)}
    result = {}
    for name in names:
        record = records[name]
        sid = record.get('session_id')
        if not sid:raise ValueError('No native session associated with '+name)
        messages = get('/api/sessions/'+sid+'/messages?profile=default&limit=30')['messages']
        tool_results = []
        for m in messages:
            if m.get('role') == 'tool' and m.get('tool_name') == 'honcho_conclude':
                try:tool_results.append(json.loads(m.get('content') or '{}'))
                except ValueError:pass
        expected = 'Herdr-launched project workers'
        conclusion_hits = [c for d in tool_results for c in d.get('conclusions',[]) if expected in c.get('content','')]
        result[name] = {'session_id':sid,'title':record['title'],
                        'desktop_listed':sid in visible,
                        'desktop_messages_read':True,'message_rows':len(messages),
                        'honcho_write_ack':any('Conclusion saved' in str(d.get('result','')) for d in tool_results),
                        'honcho_conclusion_readback':bool(conclusion_hits),
                        'cross_worker_recall_marker':any(m.get('role')=='assistant' and 'HONCHO_CROSS_WORKER_RECALL' in str(m.get('content','')) for m in messages)}
        assert result[name]['desktop_listed'], 'Worker missing from authenticated Desktop list'
        assert result[name]['honcho_conclusion_readback'], 'No actual memory tool readback in native transcript'
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--api-base',required=True)
    p.add_argument('names',nargs='+')
    a=p.parse_args()
    print(json.dumps(verify(a.api_base.rstrip('/'),a.names),indent=2))
