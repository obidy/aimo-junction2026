"""Offline recipe-agent tests: synthetic web/model responses and supplier API."""
import copy
from decimal import Decimal
import os
import unittest
from unittest.mock import patch
import aimo_api as g
import recipe_agent as r
import test_api


RECIPE = {"title":"Synthetic macaroni and milk test recipe", "source_url":"https://example.com/test-recipe",
    "source_title":"Synthetic recipe fixture", "source_servings":"4", "notes":[], "ingredients":[
        {"name":"Macaroni", "quantity":"0.4", "unit":"KG", "original_measure":"400 g", "search_terms":["macaroni"], "optional":False, "uncertainty":None},
        {"name":"Milk", "quantity":"0.2", "unit":"L", "original_measure":"200 ml", "search_terms":["milk"], "optional":False, "uncertainty":None}]}

def output(value):
    import json
    return {"status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":json.dumps(value)}]}]}


class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.fixture=test_api.GatewayTests();self.fixture.setUp();self.fixture.add_pasta()
        self.client=self.fixture.client;self.agent=self.fixture.agent;self.reviewer=self.fixture.reviewer
        self.recipe=copy.deepcopy(RECIPE)
        self.provider=patch.object(r,"provider_call",side_effect=self.fake_provider);self.provider.start()

    def tearDown(self):
        self.provider.stop();self.fixture.tearDown()

    def fake_provider(self, gateway, body):
        if "tools" in body:
            self.assertEqual(body["tool_choice"],"required")
            return {"output":[{"type":"web_search_call","action":{"sources":[{"url":RECIPE["source_url"],"title":"Synthetic source"}]}},
                {"type":"message","content":[{"type":"output_text","text":"Synthetic fixture research; not a real web lookup."}]}]}
        name=body["text"]["format"]["name"]
        if name=="sourcedrecipe": return output(self.recipe)
        import json
        supplied=json.loads(body["input"])
        return output({"matches":[{"ingredient_id":item["ingredient"]["id"], "product_ids":[p["sku"] for p in item["catalogue_candidates"]][:1],"reason":"Synthetic exact match", "requires_review":False} for item in supplied]})

    def plan(self, **kwargs):
        body={"request":"Macaroni and milk for 200 people", "portions":200,"delivery_date":self.fixture.day,**kwargs}
        response=self.client.post('/recipe-plans',headers=self.reviewer,json=body)
        self.assertEqual(response.status_code,201,response.text)
        return response.json()

    def commit(self,p,headers=None):
        return self.client.post('/recipe-plans/'+p['id']+'/approve-and-commit',headers=headers or self.reviewer,json={"fingerprint":p['fingerprint']})

    def test_scaled_whole_basket_approval_and_idempotency(self):
        p=self.plan();self.assertEqual(p['status'],'PENDING_REVIEW')
        self.assertEqual(p['total_gross_eur'],'63.10')
        self.assertEqual(p['ingredients'][0]['required_quantity'],'20.0')
        self.assertEqual(len(p['order_lines']),2)
        self.assertEqual(self.commit(p,self.agent).status_code,403)
        receipt=self.commit(p);self.assertEqual(receipt.status_code,200,receipt.text)
        result=receipt.json();self.assertFalse(result['mock_order']['upstream_order_submitted'])
        self.assertEqual(self.commit(p).json()['mock_order']['id'],result['mock_order']['id'])
        self.assertEqual(self.client.get('/proposals',headers=self.agent).json()['proposals'],[])

    def test_automatic_one_request(self):
        p=self.plan(autonomy='automatic',auto_commit=True)
        self.assertEqual(p['status'],'COMMITTED_MOCK');self.assertIsNotNone(p['mock_order'])

    def test_aggregate_budget_not_per_ingredient(self):
        with patch.dict(os.environ,{'AIMO_APPROVAL_LIMIT':'50'}):
            p=self.plan(autonomy='automatic',auto_commit=True)
            self.assertEqual(p['status'],'PENDING_REVIEW');self.assertIsNone(p['mock_order'])
            self.assertTrue(all(Decimal(b['gross'])<50 for b in p['order_lines']))

    def test_agent_cannot_enable_automatic_mode(self):
        with patch.dict(os.environ,{'AIMO_RECIPE_AUTONOMY':'review'}):
            response=self.client.post('/recipe-plans',headers=self.agent,json={'request':'Macaroni','portions':200,'delivery_date':self.fixture.day,'autonomy':'automatic'})
            self.assertEqual(response.status_code,403)

    def test_unknown_quantity_blocks_partial_recipe(self):
        self.recipe['ingredients'][1].update(quantity=None,unit='UNRESOLVED',original_measure='to taste')
        p=self.plan();self.assertEqual(p['status'],'BLOCKED');self.assertIsNone(p['total_gross_eur'])
        self.assertEqual(self.commit(p).status_code,409)

    def test_missing_yield_can_be_repaired_by_explicit_total_quantities(self):
        self.recipe['source_servings']=None;p=self.plan();self.assertEqual(p['status'],'BLOCKED')
        response=self.client.post('/recipe-plans/'+p['id']+'/rebuild',headers=self.reviewer,json={'fingerprint':p['fingerprint'],'quantities':[{'ingredient_id':'I-1','quantity':'20','unit':'KG'},{'ingredient_id':'I-2','quantity':'10','unit':'L'}]})
        self.assertEqual(response.status_code,201,response.text);self.assertEqual(response.json()['status'],'PENDING_REVIEW')
        self.assertNotEqual(response.json()['id'],p['id'])

    def test_optional_not_purchased(self):
        self.recipe['ingredients'][1]['optional']=True;p=self.plan()
        self.assertEqual(len(p['order_lines']),1);self.assertEqual(p['ingredients'][1]['status'],'OPTIONAL_NOT_ORDERED')

    def test_same_sku_combines_before_pack_rounding(self):
        self.recipe['ingredients']=[copy.deepcopy(self.recipe['ingredients'][0]) for _ in range(2)]
        for ingredient in self.recipe['ingredients']:ingredient['quantity']='0.1'
        p=self.plan();self.assertEqual(len(p['order_lines']),1);self.assertEqual(p['order_lines'][0]['quantity'],'1')

    def test_price_change_requires_new_review(self):
        p=self.plan();self.fixture.price_factor=2;self.assertEqual(self.commit(p).status_code,409)

    def test_unavailable_required_ingredient_blocks(self):
        self.fixture.stock_amount=0;p=self.plan();self.assertEqual(p['status'],'BLOCKED')

    def test_fabricated_source_rejected(self):
        self.recipe['source_url']='https://example.com/not-retrieved'
        response=self.client.post('/recipe-plans',headers=self.reviewer,json={'request':'Macaroni','delivery_date':self.fixture.day})
        self.assertEqual(response.status_code,502)

    def test_invented_sku_rejected(self):
        ingredient=r.scaled_ingredients(r.SourcedRecipe.model_validate(self.recipe),200)
        candidates=r.collect_candidates(g,ingredient)
        with patch.object(r,'json_model',return_value=r.MatchResult(matches=[r.IngredientMatch(ingredient_id='I-1',product_ids=['INVENTED'],reason='bad',requires_review=False)])):
            with self.assertRaisesRegex(RuntimeError,'outside'):r.match_candidates(g,ingredient,candidates)

    def test_piece_conversion_never_guesses_weight(self):
        self.assertIsNone(g.core.quantity_per_sales_unit(g.catalogue()[0],'PIECE',{})[0])
        self.assertIsNone(g.core.quantity_per_sales_unit(g.catalogue()[1],'PIECE',{})[0])

    def test_freeform_preferences_force_review(self):
        p=self.plan(autonomy='automatic',auto_commit=True,preferences='No wine')
        self.assertEqual(p['status'],'PENDING_REVIEW')

if __name__=='__main__':unittest.main()
