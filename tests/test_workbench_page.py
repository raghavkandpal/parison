import json
import re
import shutil
import subprocess
import unittest

from parison.workbench_page import PAGE, PLAN_PICKER_SCRIPT, POLICY_REVIEW_SCRIPT, SUITE_SERIES_SCRIPT


class WorkbenchPageTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed for the browser-script regression")
    def test_delayed_recipe_picker_cannot_replace_cleared_or_newer_state(self):
        program = r"""
const assert=require('node:assert/strict'),vm=require('node:vm');
const script=SCRIPT;
async function scenario(change,stage){
  let handler,resolveResponse,resolveBody,submitted=0;
  const context={
    planRevision:1,token:'local',recipe:{value:'original.json'},planOpenStatus:{textContent:''},
    chooseRecipe:{disabled:false,addEventListener:(event,callback)=>handler=callback},
    planForm:{requestSubmit:()=>submitted++},
    post:()=>new Promise(resolve=>resolveResponse=resolve)
  };
  vm.runInNewContext(script,context);
  const pending=handler();
  if(stage==='response')change(context);
  resolveResponse({ok:true,status:200,json:()=>new Promise(resolve=>resolveBody=resolve)});
  await Promise.resolve();
  if(resolveBody){if(stage==='body')change(context);resolveBody({recipe:'selected.json'});}
  await pending;
  return {context,submitted};
}
(async()=>{
  for(const stage of ['response','body']){
    for(const next of ['', 'newer.json']){
      const result=await scenario(state=>{state.planRevision++;state.recipe.value=next},stage);
      assert.equal(result.context.recipe.value,next);assert.equal(result.submitted,0);
    }
    const typed=await scenario(state=>state.recipe.value='typed.json',stage);
    assert.equal(typed.context.recipe.value,'typed.json');assert.equal(typed.submitted,0);
  }
  const current=await scenario(()=>{},'response');assert.equal(current.context.recipe.value,'selected.json');assert.equal(current.submitted,1);
})().catch(error=>{console.error(error);process.exitCode=1});
""".replace("SCRIPT", json.dumps(PLAN_PICKER_SCRIPT))
        checked = subprocess.run([shutil.which("node"), "-e", program], capture_output=True, text=True, check=False)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed for the browser-script regression")
    def test_policy_review_discards_late_summary_and_sensitive_details(self):
        program = r"""
const assert=require('node:assert/strict'),vm=require('node:vm');
const script=SCRIPT;
async function scenario(kind,stage){
  const elements={};
  function element(id){return elements[id]||(elements[id]={value:id,hidden:true,disabled:true,textContent:'',handlers:{},addEventListener(e,f){this.handlers[e]=f},replaceChildren(){this.rendered=null}})}
  let resolveResponse,resolveBody;
  const context={document:{getElementById:element},rows:(data,label,target)=>target.rendered=data,post:()=>new Promise(resolve=>resolveResponse=resolve)};
  vm.runInNewContext(script,context);
  const summary={review_id:'review',summary:{compatibility:'ACCEPT'}};
  async function deliver(body){resolveResponse({ok:true,json:async()=>body});await Promise.resolve();await Promise.resolve()}
  if(kind==='details'){
    const first=element('policy-review-form').handlers.submit({preventDefault(){}});await deliver(summary);await first;
    assert.equal(element('policy-details-button').disabled,false);
  }
  const pending=kind==='summary'?element('policy-review-form').handlers.submit({preventDefault(){}}):element('policy-details-button').handlers.click();
  if(stage==='response')element('policy-review-form').handlers.input();
  resolveResponse({ok:true,json:()=>new Promise(resolve=>resolveBody=resolve)});
  await Promise.resolve();
  await new Promise(setImmediate);
  if(stage==='body')element('policy-review-form').handlers.input();
  resolveBody(kind==='summary'?summary:{details:{secret:'schema-sensitive'}});
  await pending;
  assert.equal(element('policy-review-summary').hidden,true);
  assert.equal(element('policy-details-button').disabled,true);
  assert.equal(element('policy-details').textContent,'');
  assert.equal(element('policy-details').hidden,true);
}
(async()=>{for(const kind of ['summary','details'])for(const stage of ['response','body'])await scenario(kind,stage)})().catch(error=>{console.error(error);process.exitCode=1});
""".replace("SCRIPT", json.dumps(POLICY_REVIEW_SCRIPT))
        checked = subprocess.run([shutil.which("node"), "-e", program], capture_output=True, text=True, check=False)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed for the browser-script regression")
    def test_suite_series_ignores_late_review_after_bundle_edit(self):
        program = r"""
const assert=require('node:assert/strict'),vm=require('node:vm');
const elements={};function element(id){return elements[id]||(elements[id]={value:'run-1\nrun-2',hidden:true,disabled:true,textContent:'',handlers:{},addEventListener(name,callback){this.handlers[name]=callback},replaceChildren(){this.options=[]},add(option){this.options.push(option)}})}
let resolveResponse,resolveBody;
const context={document:{getElementById:element},Option:function(text,value){this.text=text;this.value=value},rows:()=>{},post:()=>new Promise(resolve=>resolveResponse=resolve)};
vm.runInNewContext(SCRIPT,context);
(async()=>{const pending=element('series-form').handlers.submit({preventDefault(){}});resolveResponse({ok:true,json:()=>new Promise(resolve=>resolveBody=resolve)});await new Promise(setImmediate);element('series-bundles').handlers.input();resolveBody({review_id:'review',series:{runs:[{},{}],cases:[{case_ref:'case',comparison_mode:'keyed',groups:[{group_id:'group',kind:'field',classification:'different'}]}]}});await pending;assert.equal(element('series-result').hidden,true);assert.equal(element('series-export').disabled,true);assert.equal(element('series-case').options.length,0)})().catch(error=>{console.error(error);process.exitCode=1});
""".replace("SCRIPT", json.dumps(SUITE_SERIES_SCRIPT))
        checked = subprocess.run([shutil.which("node"), "-e", program], capture_output=True, text=True, check=False)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_refined_ui_contract(self):
        page = PAGE.decode()

        self.assertIn("--canvas:#f4f6f9", page)
        self.assertIn(".editor-footer{align-items:stretch;flex-direction:column}", page)
        self.assertNotIn('class="eyebrow"', page)
        self.assertNotIn("@media(pointer:coarse)", page)
        self.assertIn("tbody th{width:34%}", page)
        self.assertIn("#history-view table{table-layout:fixed}", page)
        self.assertIn('id="suite-plan-form"', page)
        self.assertIn("/api/suite-plan", page)
        self.assertIn('data-view="datasets"', page)
        self.assertIn('id="dataset-review"', page)
        self.assertIn('id="dataset-publish-button" type="button" disabled', page)
        self.assertIn("/api/dataset-review", page)
        self.assertIn("/api/dataset-publish", page)
        self.assertIn('id="suite-author-form"', page)
        self.assertIn('id="author-case-form"', page)
        self.assertIn("/api/suite-draft-review", page)
        self.assertIn("/api/suite-draft-export", page)
        self.assertIn("/api/suite-series", page)
        self.assertIn("/api/suite-series-export", page)
        self.assertNotIn("}th{width:34%", page)
        self.assertNotIn("No partial bundle was published", page)
        self.assertIn("Check the output location in Results before reusing it", page)
        for activity in ("run", "history", "investigate", "compare"):
            self.assertIn(f'data-view="{activity}"', page)
            self.assertIn(f'id="{activity}-view"', page)

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed for the browser-script regression")
    def test_embedded_workbench_script_is_valid_javascript(self):
        script = re.search(r"<script>(.*?)</script>", PAGE.decode(), re.DOTALL)
        self.assertIsNotNone(script)
        checked = subprocess.run(
            [shutil.which("node"), "--check"], input=script.group(1), capture_output=True, text=True
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)


if __name__ == "__main__":
    unittest.main()
