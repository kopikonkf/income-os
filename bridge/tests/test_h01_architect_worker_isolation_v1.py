import argparse, importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from bin import die_engineering_lease as lease

ROOT=Path(__file__).resolve().parents[2]
MOD=ROOT/'company'/'company-os'/'die-h01'/'engineering'/'architect_worker_isolation.py'
RUNTIME=ROOT/'company'/'company-os'/'die-h01'/'runtime'/'h01-architect-worker-isolation.v1.json'
TASK_GRAPH=ROOT/'company'/'company-os'/'die-h01'/'die-h01-task-graph.v1.json'
SPEC=importlib.util.spec_from_file_location('h01_arch_isolation',MOD)
M=importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name]=M; SPEC.loader.exec_module(M)

def run(*args,cwd):
    return subprocess.run([*args],cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)

def commit_graph(repo,tasks,message):
    graph=repo/M.DEFAULT_TASK_GRAPH; graph.parent.mkdir(parents=True,exist_ok=True)
    graph.write_text(json.dumps({'tasks':tasks},indent=2)+'\n')
    run('git','add',str(graph.relative_to(repo)),cwd=repo); run('git','commit','-m',message,cwd=repo)
    return run('git','rev-parse','HEAD',cwd=repo).stdout.strip()

def seed_gate_repo(root):
    repo=root/'repo'; repo.mkdir(); run('git','init','-b','main',cwd=repo)
    run('git','config','user.name','H01 Test',cwd=repo); run('git','config','user.email','h01@example.invalid',cwd=repo)
    tasks=[
      {'id':'H01-A','status':'DONE','authority':'ARCHITECT','depends_on':[]},
      {'id':'H01-B','status':'READY','authority':'ARCHITECT','depends_on':['H01-A']},
      {'id':'H01-C','status':'BLOCKED','authority':'FOUNDER_REQUIRED','depends_on':['H01-B']}]
    main=commit_graph(repo,tasks,'main graph'); run('git','update-ref','refs/remotes/origin/main',main,cwd=repo)
    return repo,tasks,main

def task_workspace(root,task_id):
    sessions=root/'sessions'; states=root/'states'; claims=root/'claims'; target=sessions/task_id
    target.mkdir(parents=True); run('git','init','-b','worker',cwd=target)
    run('git','config','user.name','H01 Test',cwd=target); run('git','config','user.email','h01@example.invalid',cwd=target)
    graph=target/M.DEFAULT_TASK_GRAPH; graph.parent.mkdir(parents=True)
    graph.write_text(json.dumps({'tasks':[{'id':task_id,'status':'READY','authority':'ARCHITECT','depends_on':[]}]})+'\n')
    run('git','add','.',cwd=target); run('git','commit','-m','seed',cwd=target)
    sha=run('git','rev-parse','HEAD',cwd=target).stdout.strip(); run('git','update-ref','refs/remotes/origin/main',sha,cwd=target)
    states.mkdir(parents=True)
    (states/f'{task_id}.json').write_text(json.dumps({'schema':M.WORKTREE_SCHEMA,'task_id':task_id,'status':'OPEN',
      'worktree':str(target.resolve()),'anchor':str((root/'anchor.git').resolve()),'base_ref':M.DEFAULT_CANONICAL_REF,
      'base_sha':sha,'created_at':'2026-09-12T00:00:00Z'})+'\n')
    return target,sessions,states,claims

class WorkerIsolationTests(unittest.TestCase):
    def test_canonical_gate_ignores_unmerged_worker_branch(self):
        with tempfile.TemporaryDirectory() as td:
            repo,tasks,main=seed_gate_repo(Path(td)); run('git','checkout','-b','feature/h01-b',cwd=repo)
            changed=[dict(x) for x in tasks]; changed[1]['status']='DONE'; changed[2]['status']='READY'
            feature=commit_graph(repo,changed,'feature says dependency done'); self.assertNotEqual(feature,main)
            with self.assertRaisesRegex(M.IsolationError,'E_CANONICAL_DEPENDENCY_BLOCKED'): M.canonical_task_gate(repo,'H01-C')
            run('git','update-ref','refs/remotes/origin/main',feature,cwd=repo)
            ev=M.canonical_task_gate(repo,'H01-C'); self.assertEqual(ev['canonical_ref_sha'],feature)
            self.assertEqual(ev['dependency_status'],{'H01-B':'DONE'}); self.assertFalse(ev['scheduler_action_taken'])

    def test_exact_task_worktree_and_open_lifecycle_are_required(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); target,sessions,states,_=task_workspace(root,'H01-B')
            ev=M.validate_worker_worktree('H01-B',target,worktree_root=sessions,state_root=states,protected_root=root/'live')
            self.assertEqual(ev['worktree'],str(target.resolve())); self.assertEqual(ev['lifecycle_status'],'OPEN')
            with self.assertRaisesRegex(M.IsolationError,'E_WORKTREE_TASK_PATH_MISMATCH'):
                M.validate_worker_worktree('H01-C',target,worktree_root=sessions,state_root=states,protected_root=root/'live')

    def test_same_mutable_worktree_cannot_be_claimed_by_parallel_workers(self):
        with tempfile.TemporaryDirectory() as td:
            target,_,_,claims=task_workspace(Path(td),'H01-B'); a=M.MutableWorktreeClaim(claims,target); b=M.MutableWorktreeClaim(claims,target)
            a.acquire(M.WorkerIdentity('H01-B','architect-a','AD-A'))
            with self.assertRaisesRegex(M.IsolationError,'E_MUTABLE_WORKTREE_BUSY'): b.acquire(M.WorkerIdentity('H01-B','architect-b','AD-B'))
            self.assertEqual(a.release()['status'],'RELEASED')

    def test_corrupt_existing_claim_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            target,_,_,claims=task_workspace(Path(td),'H01-B'); c=M.MutableWorktreeClaim(claims,target)
            c.lock_dir.mkdir(parents=True); c._state_path().write_text('not-json')
            with self.assertRaisesRegex(M.IsolationError,'E_MUTABLE_WORKTREE_BUSY_CORRUPT'): c.acquire(M.WorkerIdentity('H01-B','architect-a','AD-A'))

    def test_distinct_task_worktrees_can_be_claimed_in_parallel(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ta,_,_,claims=task_workspace(root/'a','H01-A'); tb,_,_,_=task_workspace(root/'b','H01-B')
            a=M.MutableWorktreeClaim(claims,ta); b=M.MutableWorktreeClaim(claims,tb)
            a.acquire(M.WorkerIdentity('H01-A','architect-a','AD-A')); b.acquire(M.WorkerIdentity('H01-B','architect-b','AD-B'))
            self.assertEqual(a.release()['status'],'RELEASED'); self.assertEqual(b.release()['status'],'RELEASED')

    def test_protected_live_git_metadata_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); target,sessions,states,_=task_workspace(root,'H01-B')
            with self.assertRaisesRegex(M.IsolationError,'E_PROTECTED_LIVE_GIT_METADATA'):
                M.validate_worker_worktree('H01-B',target,worktree_root=sessions,state_root=states,protected_root=target/'.git')

    def test_conflicting_repo_write_lease_fails_closed_across_tasks(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'leases'; state_a=Path(td)/'a.json'; state_b=Path(td)/'b.json'
            a=argparse.Namespace(lease_root=str(root),scope='company-os',task_id='H01-A',owner='architect-a',state_file=str(state_a),ttl_seconds=600)
            b=argparse.Namespace(lease_root=str(root),scope='company-os',task_id='H01-B',owner='architect-b',state_file=str(state_b),ttl_seconds=600)
            first=lease.acquire_pair(a); self.assertEqual(first['resources'],['income-os.repo-write','company-os.H01-A'])
            with self.assertRaises(lease.LeaseBusy): lease.acquire_pair(b)
            lease.release_pair(argparse.Namespace(state_file=str(state_a)))
            second=lease.acquire_pair(b); self.assertEqual(second['resources'],['income-os.repo-write','company-os.H01-B'])
            lease.release_pair(argparse.Namespace(state_file=str(state_b)))

    def test_publication_resources_match_h01_300_contract(self):
        self.assertEqual(M.publication_resources('H01-303'),['income-os.repo-write','company-os.H01-303'])

    def test_canonical_task_graph_opens_h01_304_only_after_both_dependencies_done(self):
        graph=json.loads(TASK_GRAPH.read_text()); tasks={x['id']:x for x in graph['tasks']}
        self.assertEqual(tasks['H01-302']['status'],'DONE'); self.assertEqual(tasks['H01-303']['status'],'DONE')
        self.assertEqual(tasks['H01-304']['depends_on'],['H01-302','H01-303']); self.assertEqual(tasks['H01-304']['status'],'READY')
        self.assertEqual(tasks['H01-304']['authority'],'FOUNDER_REQUIRED')

    def test_runtime_contract_forbids_linux_shadow_publication_lease(self):
        runtime=json.loads(RUNTIME.read_text())
        self.assertFalse(runtime['publication']['linux_shadow_lease_allowed'])
        self.assertEqual(runtime['publication']['resources'],['income-os.repo-write','company-os.<task_id>'])
        self.assertEqual(runtime['dependency_gate']['canonical_ref'],'refs/remotes/origin/main')
        self.assertFalse(runtime['dependency_gate']['unmerged_worker_branch_can_unlock_downstream'])
        self.assertFalse(runtime['workspace']['shared_mutable_worktree_allowed'])

if __name__=='__main__': unittest.main()
