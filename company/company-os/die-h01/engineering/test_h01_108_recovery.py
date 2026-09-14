import tempfile,unittest,json,time
from pathlib import Path
from h01_108_autonomous_supervisor import generated,committed_pending,terminal_output_mismatch,recoverable_pending_for_item,redistribution_provider,next_global_attempt_id
from h01_108_postprocess_queue import candidates

class RecoveryTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name);self.w=self.r/'001-book-qwen-a1';self.w.mkdir();self.i={'batch_position':1,'canonical_name':'book'}
 def tearDown(self):self.t.cleanup()
 def put(self,name,obj,workspace=None):
  w=workspace or self.w;p=w/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(obj))
 def complete_generation(self,workspace=None):
  w=workspace or self.w
  self.put('final/h01-103-validation.json',{'status':'PASS','canonical_svg_sha256':'c'},w)
  self.put('generation-complete.receipt.json',{'status':'GENERATION_COMPLETE','canonical_svg_sha256':'c'},w)
 def test_generation_requires_both_generation_receipt_and_h01_103(self):
  self.put('final/h01-103-validation.json',{'status':'PASS','canonical_svg_sha256':'c'});self.assertFalse(generated(self.r,self.i))
  self.put('generation-complete.receipt.json',{'status':'GENERATION_COMPLETE','canonical_svg_sha256':'c'});self.assertTrue(generated(self.r,self.i))
  self.put('asset-receipt.json',{'status':'BLOCKED_RIGHTS','rights':'BLOCK'});self.assertTrue(generated(self.r,self.i))
 def test_committed_never_eligible_for_new_dispatch(self):
  self.put('provider-dispatch.receipt.json',{'status':'COMMITTED','provider':'qwen'});self.assertIsNotNone(committed_pending(self.r,self.i,'qwen'))
 def test_postproduction_requires_generation_terminal_and_retry_is_bounded(self):
  self.complete_generation();self.put('postproduction-state.json',{'status':'PARKED_POSTPRODUCTION_RETRY'});self.assertEqual(candidates(self.r),[self.w])
  self.put('postproduction-retry.json',{'attempts':2});self.assertEqual(candidates(self.r),[])
  self.put('postproduction-retry.json',{'attempts':0,'next_retry_epoch':time.time()+3600});self.assertEqual(candidates(self.r),[])
 def test_rights_terminal_does_not_change_generation_truth(self):
  self.complete_generation();self.put('asset-receipt.json',{'postproduction_classification':'BLOCKED_RIGHTS','rights':'BLOCK'});self.assertTrue(generated(self.r,self.i));self.assertEqual(candidates(self.r),[])
 def test_wrong_modality_is_terminal_for_provider_but_redistributable(self):
  self.i.update({'planned_provider':'qwen','adaptive_provider_redistribution_allowed':True})
  self.put('provider-dispatch.receipt.json',{'status':'COMMITTED','provider':'qwen'});self.put('committed-output-recovery.receipt.json',{'status':'PROVIDER_OUTPUT_WRONG_MODALITY_RASTER','provider_output_kind':'PNG_IMAGE','do_not_acquire_other_turn_svg':True})
  self.assertEqual(terminal_output_mismatch(self.r,self.i,'qwen')['provider_output_kind'],'PNG_IMAGE');self.assertIsNone(recoverable_pending_for_item(self.r,self.i));self.assertEqual(redistribution_provider(self.r,self.i,['qwen','claude'],12,1),'claude');self.assertEqual(next_global_attempt_id(self.r,self.i),2)
 def test_wrong_modality_requires_do_not_acquire_other_turn_guard(self):
  self.i.update({'planned_provider':'qwen','adaptive_provider_redistribution_allowed':True});self.put('provider-dispatch.receipt.json',{'status':'COMMITTED','provider':'qwen'});self.put('committed-output-recovery.receipt.json',{'status':'PROVIDER_OUTPUT_WRONG_MODALITY_RASTER'})
  self.assertIsNone(terminal_output_mismatch(self.r,self.i,'qwen'));self.assertIsNotNone(recoverable_pending_for_item(self.r,self.i))
 def test_redistribution_waits_if_fallback_has_committed_recoverable_output(self):
  self.i.update({'planned_provider':'qwen','adaptive_provider_redistribution_allowed':True});self.put('provider-dispatch.receipt.json',{'status':'COMMITTED','provider':'qwen'});self.put('committed-output-recovery.receipt.json',{'status':'PROVIDER_OUTPUT_WRONG_MODALITY_RASTER','do_not_acquire_other_turn_svg':True})
  c=self.r/'001-book-claude-a2';c.mkdir();self.put('provider-dispatch.receipt.json',{'status':'COMMITTED','provider':'claude'},c)
  self.assertEqual(recoverable_pending_for_item(self.r,self.i)['provider'],'claude');self.assertIsNone(redistribution_provider(self.r,self.i,['claude','chatgpt'],12,1))
 def test_redistribution_is_bounded_to_one_provider_switch(self):
  self.i.update({'planned_provider':'qwen','adaptive_provider_redistribution_allowed':True});self.put('provider-dispatch.receipt.json',{'status':'COMMITTED','provider':'qwen'});self.put('committed-output-recovery.receipt.json',{'status':'PROVIDER_OUTPUT_WRONG_MODALITY_RASTER','do_not_acquire_other_turn_svg':True})
  c=self.r/'001-book-claude-a2';c.mkdir();self.put('provider-dispatch.receipt.json',{'status':'COMMITTED','provider':'claude'},c);self.put('committed-output-recovery.receipt.json',{'status':'PROVIDER_OUTPUT_WRONG_MODALITY_RASTER','do_not_acquire_other_turn_svg':True},c)
  self.assertIsNone(redistribution_provider(self.r,self.i,['chatgpt'],12,1))

if __name__=='__main__':unittest.main()
