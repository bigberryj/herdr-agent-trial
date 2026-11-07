import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import workers


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patch = patch.object(workers, 'RUNTIME', self.root/'runtime')
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.memory_guard = workers.local_memory_preflight
        m = patch.object(workers, 'local_memory_preflight', return_value={'endpoint':'http://127.0.0.1:33179','workspace':'hermes'})
        m.start()
        self.addCleanup(m.stop)

    def test_name_rejects_shell_and_path_tokens(self):
        for name in ('../bad', 'x;touch q', 'A', '', 'a'*25, 'a b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                workers.validate_name(name)

    def test_native_flags_preserve_memory_and_history(self):
        cmd = workers.argv('native-id', self.root/'prompt')
        self.assertEqual(cmd[0:2], ['chat', '--cli'])
        for forbidden in ('--safe-mode', '--ignore-rules', '--ignore-user-config', '--oneshot', '--yolo', '--model', '--provider', '--toolsets'):
            self.assertNotIn(forbidden, cmd)
        self.assertEqual(cmd[cmd.index('--resume')+1], 'native-id')
        self.assertIn('--query-file', cmd)

    def test_private_record_store_and_atomic_save(self):
        with workers.records() as data:
            data['one'] = {'name':'one'}
        p = workers.RUNTIME/'workers.json'
        self.assertEqual(p.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(p.read_text())['one']['name'], 'one')

    def test_repeated_name_does_not_start_or_prompt_again(self):
        with workers.records() as data:
            data['one']={'name':'one','title':'[Herdr] one'}
        with patch.object(workers,'route',return_value=('native','model')), patch.object(workers,'native_session',return_value='native-id'), patch.object(workers,'run') as run, patch.object(workers,'ensure_server') as ensure:
            result=workers.start('one',self.root,'do not replay')
            run.assert_not_called()
            ensure.assert_not_called()
            self.assertEqual(result['session_id'],'native-id')

    def test_two_managed_agents_is_a_hard_cap(self):
        with patch.object(workers,'route',return_value=('native','model')), patch.object(workers,'ensure_server'), patch.object(workers,'run',return_value={'result':{'agents':[{'name':'hw-a'},{'name':'hw-b'}]}}):
            with self.assertRaisesRegex(RuntimeError,'Two managed'):
                workers.start('three',self.root,'third')

    def test_ambiguous_start_preserves_mapping_without_resubmit(self):
        def fake(args, **kw):
            if args[:2]==['agent','list']:
                return {'result':{'agents':[]}}
            if args[:2]==['workspace','create']:
                return {'result':{'root_pane':{'pane_id':'w9:p7'},'workspace':{'workspace_id':'w9'}}}
            if args[:2]==['agent','start']:
                raise RuntimeError('timeout but admitted')
            self.fail(str(args))
        with patch.object(workers,'create_native_session',return_value='native-id'), patch.object(workers,'route',return_value=('native','model')), patch.object(workers,'ensure_server'), patch.object(workers,'native_session',return_value=None), patch.object(workers,'run',side_effect=fake):
            result=workers.start('one',self.root,'synthetic',3)
        self.assertEqual(result['launch_status'],'inspect_required')
        with workers.records() as data:
            self.assertEqual(data['one']['pane_id'],'w9:p7')
        self.assertEqual((workers.RUNTIME/'one.prompt.txt').stat().st_mode & 0o777,0o600)

    def test_invalid_budget_fails_before_external_actions(self):
        with patch.object(workers,'run') as run:
            with self.assertRaises(ValueError):
                workers.start('one',self.root,'synthetic',41)
            run.assert_not_called()

    def test_prior_prompt_is_not_silently_replayed(self):
        workers.RUNTIME.mkdir()
        (workers.RUNTIME/'one.prompt.txt').write_text('old admission')
        with patch.object(workers,'route',return_value=('native','model')), patch.object(workers,'ensure_server'), patch.object(workers,'run',return_value={'result':{'agents':[]}}) as run:
            with self.assertRaisesRegex(RuntimeError,'Prior prompt'):
                workers.start('one',self.root,'new prompt')
            self.assertEqual(run.call_count,1)

    def test_cloud_or_disabled_honcho_is_refused(self):
        home=self.root/'home';home.mkdir()
        (home/'config.yaml').write_text('memory:\n  provider: honcho\nplugins:\n  enabled: [honcho]\n')
        for url,enabled in [('https://api.honcho.dev',True),('http://127.0.0.1:33179',False)]:
            (home/'honcho.json').write_text(json.dumps({'hosts':{'hermes':{'baseUrl':url,'enabled':enabled}}}))
            with patch.object(workers,'HOME',home), patch.dict(workers.os.environ,{},clear=True):
                with self.assertRaisesRegex(RuntimeError,'LOCAL Honcho'):
                    self.memory_guard()

    def test_bypass_environment_is_refused(self):
        with patch.dict(workers.os.environ,{'HERMES_SAFE_MODE':'1'},clear=True):
            with self.assertRaisesRegex(RuntimeError,'Bypass environment'):
                self.memory_guard()

    def test_existing_live_worker_resume_is_idempotent(self):
        rec={'name':'one','agent_name':'hw-one','title':'[Herdr] one','session_id':'native-id'}
        with patch.object(workers,'ensure_server'), patch.object(workers,'native_session',return_value='native-id'), patch.object(workers,'run',return_value={'result':{'agents':[{'name':'hw-one'}]}}) as run:
            self.assertEqual(workers.resume_worker(rec)['session_id'],'native-id')
            self.assertEqual(run.call_count,1)

    def test_ambiguous_admission_has_durable_request_before_launch(self):
        def create(*args):
            stored=json.loads((workers.RUNTIME/'workers.json').read_text())['one']
            self.assertEqual(stored['request_id'],args[-1])
            raise RuntimeError('creation response lost')
        def fake(args, **kw):
            if args[:2]==['agent','list']:return {'result':{'agents':[]}}
            return {'result':{'root_pane':{'pane_id':'w1:p1'},'workspace':{'workspace_id':'w1'}}}
        with patch.object(workers,'route',return_value=('native','model')), patch.object(workers,'ensure_server'), patch.object(workers,'run',side_effect=fake), patch.object(workers,'create_native_session',side_effect=create), patch.object(workers,'native_session',return_value=None):
            result=workers.start('one',self.root,'synthetic')
        self.assertEqual(result['launch_status'],'inspect_required')

    def test_native_settlement_not_badge_is_required(self):
        base={'messages':[{'role':'user','content':'task'},{'role':'assistant','content':'result'}], 'running':False,'pending':[],'prompts':[]}
        self.assertTrue(workers.settled(base,'task'))
        for change in ({'running':True},{'pending':[{'queued':1}]},{'prompts':[{'approval':1}]},{'messages':[]},{'messages':[{'role':'user','content':'other'},{'role':'assistant','content':'result'}]},{'messages':[{'role':'user','content':'task'},{'role':'assistant','tool_calls':[{'name':'file'}]}]}):
            with self.subTest(change=change):self.assertFalse(workers.settled({**base,**change},'task'))

    def test_gateway_toolsets_are_an_array(self):
        self.assertIsInstance(workers.TOOLS, list)

    def test_server_incompatible_never_restarts(self):
        from types import SimpleNamespace
        result=SimpleNamespace(returncode=0,stdout='status: running\nendpoint_compatible: no')
        with patch.object(workers.subprocess,'run',return_value=result), patch.object(workers.subprocess,'Popen') as popen:
            with self.assertRaisesRegex(RuntimeError,'incompatible'):
                workers.ensure_server()
            popen.assert_not_called()


if __name__=='__main__':
    unittest.main()
