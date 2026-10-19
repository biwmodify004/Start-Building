import test from 'node:test';
import assert from 'node:assert/strict';
import {localAIConfig,completionPayload} from '../scripts/ai-config.mjs';

test('local Research supports Ollama and LM Studio defaults while preserving existing custom configuration',()=>{
 assert.equal(localAIConfig({AI_PROVIDER:'ollama',AI_MODEL:'fixture:latest'}).base,'http://127.0.0.1:11434/v1');
 assert.equal(localAIConfig({AI_PROVIDER:'lm-studio'}).base,'http://127.0.0.1:1234/v1');
 const legacy=localAIConfig({AI_BASE_URL:'https://fixture.test/custom/v1/',AI_MODEL:'legacy',AI_API_KEY:'fixture-secret'});
 assert.equal(legacy.base,'https://fixture.test/custom/v1');assert.equal(legacy.provider,'openai-compatible');
});
test('Ollama Research requests JSON and never puts server credentials into the model payload',()=>{
 const config=localAIConfig({AI_PROVIDER:'ollama',AI_MODEL:'fixture:latest',AI_API_KEY:'fixture-secret'}),messages=[{role:'user',content:'Fixture only'}],payload=completionPayload(config,messages);
 assert.deepEqual(payload.response_format,{type:'json_object'});assert.equal(payload.stream,false);assert.equal(payload.model,'fixture:latest');assert.deepEqual(payload.messages,messages);assert.ok(!JSON.stringify(payload).includes('fixture-secret'));assert.equal(completionPayload(localAIConfig({AI_MODEL:'legacy'}),messages).response_format,undefined);
});
test('AI endpoints reject unknown providers, embedded keys and public plaintext HTTP',()=>{
 assert.throws(()=>localAIConfig({AI_PROVIDER:'unknown'}),/AI_PROVIDER/);
 for(const base of ['http://public.example/v1','https://user:password@fixture.test/v1','https://fixture.test/v1?api_key=secret','https://fixture.test/v1#secret'])assert.throws(()=>localAIConfig({AI_BASE_URL:base}));
 assert.equal(localAIConfig({AI_BASE_URL:'http://[::1]:11434/v1'}).base,'http://[::1]:11434/v1');
});
