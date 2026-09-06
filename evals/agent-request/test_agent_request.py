#!/usr/bin/env python3
import copy, json, sys, unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import validator as v
import transport as t

ROOT=Path(__file__).parent

def request():
    return {"schema_version":v.VERSION,"agent_id":"agent_reviewer","run_id":"run_review_001","task_id":"task_issue_101","parent_run_id":"run_parent_001","action_id":"act_read_001","phase":"review","context_lane":"normal","reasoning_lane":"medium","model_class":"local-general","privacy_class":"internal","capabilities":["scm:read"],"approval":{"state":"not-required","action_id":"act_read_001","grant_id":None},"policy_bundle":"policy_public_001","issued_at":"2026-01-01T00:00:00Z","expires_at":"2026-01-01T00:04:00Z","nonce":"nonce_read_0000001","provenance":{"dispatcher_run_id":"run_dispatch_001","sequence":7}}

def context():
    grant=v.ApprovalGrant("grant_read_001","issuer_dispatch_001","agent_reviewer","run_review_001","task_issue_101","act_read_001",frozenset(v.PRIVILEGED),datetime(2026,1,1,0,5,tzinfo=timezone.utc))
    return v.TrustedContext("issuer_dispatch_001","agent_reviewer","run_review_001","task_issue_101","act_read_001",frozenset({"policy_public_001"}),frozenset(v.MODEL_CLASSES),frozenset(v.CAPABILITIES),datetime(2026,1,1,0,1,tzinfo=timezone.utc),frozenset({"run_parent_001"}),{"grant_read_001":grant})

def set_path(obj,key,value):
    parts=key.split("."); target=obj
    for part in parts[:-1]: target=target[part]
    target[parts[-1]]=value

class ContractTests(unittest.TestCase):
    def test_valid_read_and_replay_consumption(self):
        ctx=context(); self.assertEqual("allow",v.validate_request(request(),ctx,consume=True)["decision"])
        with self.assertRaisesRegex(v.ValidationError,"REPLAYED_NONCE"): v.validate_request(request(),ctx)
    def test_counterfeit_corpus(self):
        corpus=json.loads((ROOT/"fixtures/counterfeits.json").read_text())
        for row in corpus:
            with self.subTest(row=row["name"]):
                req=request(); ctx=context()
                for key,value in row.get("request_set",{}).items(): set_path(req,key,value)
                for key,value in row.get("context_set",{}).items(): setattr(ctx,key,set(value) if key=="seen_nonces" else value)
                with self.assertRaises(v.ValidationError) as caught: v.validate_request(req,ctx)
                self.assertEqual(row["expected"],caught.exception.code)
    def test_exact_grant_allows_only_bound_action(self):
        req=request(); req.update(phase="implement",capabilities=["filesystem:workspace-write"]); req["approval"]={"state":"granted","action_id":req["action_id"],"grant_id":"grant_read_001"}
        self.assertEqual("allow",v.validate_request(req,context())["decision"])
        bad=context(); g=bad.approval_grants["grant_read_001"]; bad.approval_grants["grant_read_001"]=v.ApprovalGrant(g.grant_id,g.issuer_id,g.agent_id,g.run_id,"task_other_001",g.action_id,g.capabilities,g.expires_at)
        with self.assertRaisesRegex(v.ValidationError,"APPROVAL_SCOPE_MISMATCH"): v.validate_request(req,bad)
    def test_expired_grant_rejected(self):
        req=request(); req.update(phase="implement",capabilities=["filesystem:workspace-write"]); req["approval"]={"state":"granted","action_id":req["action_id"],"grant_id":"grant_read_001"}; ctx=context(); g=ctx.approval_grants["grant_read_001"]
        ctx.approval_grants[g.grant_id]=v.ApprovalGrant(g.grant_id,g.issuer_id,g.agent_id,g.run_id,g.task_id,g.action_id,g.capabilities,ctx.now)
        with self.assertRaisesRegex(v.ValidationError,"APPROVAL_EXPIRED"): v.validate_request(req,ctx)
    def test_parent_is_provenance_not_inherited_authority(self):
        req=request(); ctx=context(); ctx.capability_ceiling=frozenset({"scm:read"}); req.update(phase="implement",capabilities=["filesystem:workspace-write"]); req["approval"]={"state":"granted","action_id":req["action_id"],"grant_id":"grant_read_001"}
        with self.assertRaisesRegex(v.ValidationError,"CAPABILITY_EXCEEDS_CEILING"): v.validate_request(req,ctx)
    def test_deep_and_complex_inputs_rejected_before_serialization(self):
        req=request(); req["unknown"]={"a":{"b":{"c":{"d":{"e":"x"}}}}}
        with self.assertRaisesRegex(v.ValidationError,"REQUEST_STRUCTURE_TOO_DEEP"): v.validate_request(req,context())
        req=request(); req["unknown"]=[0]*129
        with self.assertRaisesRegex(v.ValidationError,"REQUEST_TOO_COMPLEX"): v.validate_request(req,context())
    def test_oversized_canonical_request_rejected(self):
        req=request(); req["unknown"]="x"*5000
        with self.assertRaisesRegex(v.ValidationError,"REQUEST_TOO_LARGE"): v.validate_request(req,context())
    def test_boolean_sequence_rejected(self):
        req=request(); req["provenance"]["sequence"]=True
        with self.assertRaisesRegex(v.ValidationError,"PROVENANCE_INVALID"): v.validate_request(req,context())
    def test_schema_and_validator_constant_sets_match(self): v.self_check()
    def test_all_documented_examples_validate(self):
        for path in sorted((ROOT.parent.parent/"docs/agent-request/examples").glob("*.json")):
            wrapper=json.loads(path.read_text()); v.validate_request(wrapper["request"],v.context_from_json(wrapper["trusted_context"]))
    def test_transport_round_trip(self): self.assertEqual(request(),t.decode_headers(t.encode_headers(request())))
    def test_transport_duplicate_case_insensitive(self):
        headers=t.encode_headers(request())
        with self.assertRaisesRegex(v.ValidationError,"DUPLICATE_METADATA_HEADER"): t.decode_headers(headers+[(t.METADATA_HEADER.lower(),headers[1][1])])
    def test_transport_injection(self):
        with self.assertRaisesRegex(v.ValidationError,"HEADER_INJECTION"): t.decode_headers([(t.SCHEMA_HEADER,v.VERSION),(t.METADATA_HEADER,"abc\r\nInjected: yes")])
    def test_transport_malformed_base64(self):
        with self.assertRaisesRegex(v.ValidationError,"MALFORMED_METADATA_HEADER"): t.decode_headers([(t.SCHEMA_HEADER,v.VERSION),(t.METADATA_HEADER,"***")])
    def test_transport_header_count_bound(self):
        with self.assertRaisesRegex(v.ValidationError,"TOO_MANY_HEADERS"): t.decode_headers([("X-Fill",str(i)) for i in range(65)])
    def test_openai_mapping_contains_no_body_or_auth(self): self.assertEqual({"extra_headers"},set(t.openai_request_kwargs(request())))

if __name__=="__main__": unittest.main()
