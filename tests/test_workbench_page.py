import json
import shutil
import subprocess
import unittest

from parison.workbench_page import PAGE, PLAN_PICKER_SCRIPT


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

    def test_refined_ui_contract(self):
        page = PAGE.decode()

        self.assertIn("--canvas:#f4f6f9", page)
        self.assertIn(".editor-footer{align-items:stretch;flex-direction:column}", page)
        self.assertNotIn('class="eyebrow"', page)
        self.assertNotIn("@media(pointer:coarse)", page)
        self.assertIn("tbody th{width:34%}", page)
        self.assertIn("#history-view table{table-layout:fixed}", page)
        self.assertNotIn("}th{width:34%", page)
        for activity in ("run", "history", "investigate", "compare"):
            self.assertIn(f'data-view="{activity}"', page)
            self.assertIn(f'id="{activity}-view"', page)


if __name__ == "__main__":
    unittest.main()
