"""Synthetic FLAI policy experiment; not agronomic validation.
Run from backend root: python scripts/simulate_flai.py
Scenarios include stale/low-quality evidence, false alarms/missed threats,
rainfall variation, observation delay, intervention failure, and recovery error.
"""
import json, random, statistics
from app.services.learning.flai_engine import decide, compare_policies
random.seed(7)

POLICIES = ("fixed_threshold", "risk_only", "expected_utility", "flai_constrained_recovery_aware")

def make_scenario(i):
    threat = random.random() < 0.30
    urgent = threat and random.random() < 0.25
    # A noisy classifier can generate both false alarms and missed threats.
    observed_positive = (threat if random.random() > 0.18 else not threat)
    quality = random.choice([0.15, 0.4, 0.7, 0.95])
    freshness = random.choice([0.15, 0.5, 1.0])  # stale evidence represented by low freshness
    rainfall_mm = random.choice([0, 0, 2, 8, 20])
    intervention_fails = random.random() < 0.20
    delayed_observation = random.random() < 0.25
    lr = 4.0 if observed_positive else 0.35
    # Synthetic action estimates only. These values must never be used as field settings.
    actions = [
        {"action_type":"MONITOR","expected_recovery_benefit":1.0,"action_cost":0.2,"resource_cost":0.1,"side_effect_cost":0.0,"serious_harm_probability":0.005,"serious_harm_loss":100,"loss_samples":[0,0,1,0],"feasible":True,"supported_by_evidence":True},
        {"action_type":"VERIFY","expected_recovery_benefit":1.5,"action_cost":0.4,"resource_cost":0.1,"side_effect_cost":0.0,"serious_harm_probability":0.005,"serious_harm_loss":100,"loss_samples":[0,0,1,0],"feasible":True,"supported_by_evidence":True},
        {"action_type":"TREAT","expected_recovery_benefit":7.0 if threat else 0.5,"action_cost":1.5,"resource_cost":1.0,"side_effect_cost":1.0,"serious_harm_probability":0.03 if threat else 0.08,"serious_harm_loss":100,"loss_samples":[0,2,5,20 if not threat else 3],"feasible":True,"supported_by_evidence":True},
    ]
    # A simulated positive VoI is more likely when evidence is weak; delay can make waiting unsafe.
    voi = {"provided":True,"expected_best_utility_after_observation":3.0 if quality < 0.6 else 2.2,
           "current_best_utility":1.8,"measurement_cost":0.3,
           "delay_cost":1.2 if urgent or delayed_observation else 0.2,
           "waiting_safe":not urgent and not (delayed_observation and threat)}
    # Recovery discrepancy includes random measurement noise and occasional failed response.
    expected = 5.0
    observed = expected + random.gauss(0, 1.0) + (3.0 if intervention_fails else 0.0)
    recovery = {"provided":True,"observed_value":observed,"expected_value":expected,
                "observed_variance":1.0,"expected_variance":1.0,"z_threshold":2.0,
                "evidence_valid":quality >= 0.4,"timing_appropriate":not delayed_observation}
    req = {"prior_threat_probability":0.25,"evidence":[{"name":"synthetic_sensor_or_vision","likelihood_ratio":lr,"quality":quality,"freshness":freshness,"validity":1.0}],
           "actions":actions,"risk_limit":0.05,"cvar_weight":0.5,"cvar_alpha":0.75,"voi":voi,"recovery":recovery}
    return {"request":req,"truth":{"threat":threat,"urgent":urgent,"rainfall_mm":rainfall_mm,
                                     "intervention_fails":intervention_fails,"delayed_observation":delayed_observation,
                                     "recovery_error":observed-expected}}

def realized_metrics(action, truth):
    threat=truth['threat']; urgent=truth['urgent']; failed=truth['intervention_fails']
    # Simple illustrative outcome model; not a crop-specific yield or harm model.
    treatment=(action == 'TREAT')
    monitoring=(action in ('MONITOR','VERIFY'))
    unnecessary=1 if treatment and not threat else 0
    crop_loss=(0.8 if treatment and threat and not failed else (4.0 if threat else 0.3))
    if truth['rainfall_mm'] >= 8 and action == 'IRRIGATE': crop_loss += 1.0
    serious_harm=1 if (treatment and not threat and random.random()<0.08) or (urgent and monitoring and truth['delayed_observation']) else 0
    action_cost={'MONITOR':0.2,'VERIFY':0.4,'TREAT':1.5,'ESCALATE':1.0}.get(action,1.0)
    resource={'MONITOR':0.1,'VERIFY':0.1,'TREAT':1.0,'ESCALATE':0.1}.get(action,0.2)
    return {"total_cost":action_cost+resource+crop_loss,"crop_loss":crop_loss,"resource_use":resource,
            "unnecessary_interventions":unnecessary,"serious_harm":serious_harm,
            "monitoring_frequency":1 if monitoring else 0,"recovery_error_abs":abs(truth['recovery_error'])}

def main(n=500):
    sums={p:{k:0.0 for k in ("total_cost","crop_loss","resource_use","unnecessary_interventions","serious_harm","monitoring_frequency","recovery_error_abs")} for p in POLICIES}
    counts={p:{} for p in POLICIES}
    for i in range(n):
        sc=make_scenario(i); req=sc['request']; truth=sc['truth']
        comparison=compare_policies(req)
        out=decide(req)
        choices={p:comparison['policies'][p]['selected_action'] for p in POLICIES if p != 'flai_constrained_recovery_aware'}
        choices['flai_constrained_recovery_aware']=out['selected_action']
        for policy, action in choices.items():
            counts[policy][action]=counts[policy].get(action,0)+1
            metrics=realized_metrics(action,truth)
            for k,v in metrics.items(): sums[policy][k]+=v
    results={}
    for policy in POLICIES:
        results[policy]={"action_counts":counts[policy],"mean_metrics":{k:round(v/n,4) for k,v in sums[policy].items()}}
    print(json.dumps({"warning":"Synthetic plumbing experiment only. Inputs/outcomes are fabricated; do not interpret as agronomic evidence.","scenarios":n,"results":results},indent=2))

if __name__ == '__main__': main()
