import json, hashlib
EV=b"nono.audit.event.alpha\n"; CH=b"nono.audit.chain.alpha\n"; MK=b"nono.audit.merkle.alpha\n"
def dumps(o): return json.dumps(o, separators=(',',':'), ensure_ascii=False)
def leaf(b): return hashlib.sha256(EV+b).digest()
def chain(prev, lf): return hashlib.sha256(CH+(prev if prev else b"\0"*32)+lf).digest()
def merkle(leaves):
    lvl=list(leaves)
    while len(lvl)>1:
        nxt=[]
        for i in range(0,len(lvl),2):
            if i+1==len(lvl): nxt.append(lvl[i])
            else: nxt.append(hashlib.sha256(MK+lvl[i]+lvl[i+1]).digest())
        lvl=nxt
    return lvl[0]
# golden vector check
g={"type":"capability_decision","entry":{"timestamp":{"secs_since_epoch":5,"nanos_since_epoch":0},"request":{"capability_type":"capability","request_id":"req-1","path":"/tmp/example","access":"ReadWrite","reason":"need scratch space","child_pid":42,"session_id":"sess-1"},"decision":{"Denied":{"reason":"outside policy"}},"backend":"terminal","duration_ms":12}}
assert leaf(dumps(g).encode()).hex()=="fb0ff01abb9de69f3c50deb6b828a25d941d7541856d81b8fa3da84b95aa125a", "golden mismatch"
print("golden vector OK")

S="019a2c1e-5f60-7c3a-9b1d-4e2f8a7c6d10"
T0=1789663200  # 2026-09-16T16:40:00Z
events=[
 {"type":"session_started","started":"2026-09-16T16:40:00.000Z","command":["claude","--print","open a PR for the changelog fix"]},
 {"type":"sandbox_runtime","event":{"timestamp":"2026-09-16T16:40:00.041Z","platform":"linux","landlock_abi":"6","landlock_execute_enforced":True,"tool_sandbox_active":True}},
 {"type":"capability_decision","entry":{"timestamp":{"secs_since_epoch":T0+61,"nanos_since_epoch":118000000},"request":{"capability_type":"capability","request_id":"01K5ATQ2W8H0R7M3F1Z9C4X6DE","path":"/home/sal/.ssh/id_ed25519","access":"Read","reason":"read deploy key for git push","child_pid":48213,"session_id":S},"decision":{"Denied":{"reason":"denied by operator"}},"backend":"terminal","duration_ms":6420}},
 {"type":"command_policy","event":{"timestamp":"2026-09-16T16:41:07.512Z","session_id":S,"command":"git","caller":"session","caller_kind":"session","caller_pid":48213,"shim_pid":48377,"session_root_pid":48201,"decision":"allow","reason":"command_policies.commands.git.from.session","stdio_mode":"inherit","argv_hash":"9c1f2e7a4d0b6e8f3a5c7d9e1b2f4a6c8e0d2f4b6a8c0e2d4f6a8b0c2e4d6f8a","env_name_hash":"3e8a1c5d7f9b2e4a6c8d0f1b3a5c7e9d2f4a6b8c0e1d3f5a7b9c2e4d6f8a0b1c","cwd_hash":"6b2d4f8a0c1e3a5c7e9b1d3f5a7c9e2b4d6f8a0c1e3b5d7f9a2c4e6b8d0f1a3c","argv_display":["git","push","origin","fix/changelog-links"],"env_names_display":["HOME","PATH","GIT_SSH_COMMAND"],"cwd_display":"/home/sal/src/nono","exit_code":0}},
 {"type":"capability_decision","entry":{"timestamp":{"secs_since_epoch":T0+72,"nanos_since_epoch":330000000},"request":{"capability_type":"endpoint","request_id":"01K5ATQKX3P9V2N6D8R1B5Y7ZQ","route_id":"github","upstream":"https://api.github.com","method":"POST","path":"/repos/nolabs-ai/nono/pulls","rule_label":"github.write","reason":"write to upstream repository requires approval","child_pid":48213,"session_id":S},"decision":"Granted","backend":"webhook","duration_ms":4218}},
 {"type":"network","event":{"timestamp_unix_ms":(T0+76)*1000+551,"mode":"reverse","decision":"approve_granted","route_id":"github","auth_mechanism":"spiffe_jwt_bearer","auth_outcome":"succeeded","managed_credential_active":True,"injection_mode":"spiffe_jwt","endpoint_policy_action":"approve","endpoint_policy_rule":"github.write","approval_backend":"webhook","spiffe_context":{"workload_spiffe_id":"spiffe://nolabs.example/agent/claude-code/laptop-sal","trust_domain":"nolabs.example","svid_type":"jwt","source":"workload_api","upstream_spiffe_id":"spiffe://nolabs.example/broker/github","delegation":{"authorized_by":"spiffe://nolabs.example/session/019a2c1e","on_behalf_of":"spiffe://nolabs.example/user/sal","chain_depth":1}},"target":"api.github.com","upstream":"https://api.github.com","port":None,"method":"POST","path":"/repos/nolabs-ai/nono/pulls","status":201,"reason":None}},
 {"type":"session_ended","ended":"2026-09-16T16:41:20.904Z","exit_code":0},
]
prev=None; leaves=[]; lines=[]
for i,ev in enumerate(events):
    b=dumps(ev).encode(); lf=leaf(b); ch=chain(prev,lf)
    rec={"sequence":i,"prev_chain":prev.hex() if prev else None,"leaf_hash":lf.hex(),"chain_hash":ch.hex(),"event_json":b.decode(),"event":ev}
    lines.append(dumps(rec)); leaves.append(lf); prev=ch
summary={"hash_algorithm":"sha256","event_count":len(events),"chain_head":prev.hex(),"merkle_root":merkle(leaves).hex()}
open("audit-events.ndjson","w").write("\n".join(lines)+"\n")
open("integrity.json","w").write(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
for l in lines: print(l[:110]+"...")
