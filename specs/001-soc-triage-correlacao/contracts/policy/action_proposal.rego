package soc_agent.policy.action_proposal

# PolicyEngine (OPA/Rego) — evaluated BEFORE any action proposal is emitted/finalized.
# Input contract: contracts/schemas/policy-decision.request.schema.json
# Output shape mapped to: contracts/schemas/policy-decision.response.schema.json
#
# Constitutional alignment: R2 (propose only, explicit approval required),
# R4 (escalate on uncertainty), R5 (rollback before approval/proposal validity),
# R7 (query proposals are reviewable artifacts; no production execution by agent).

default result := "block_and_escalate"

default reasons := ["policy_default_deny: no allow conditions satisfied"]

# Final decision object (adapter maps/augments ids/timestamps/versions as needed)
decision := {
	"result": result,
	"reasons": reasons,
	"required_actions": required_actions,
}

required_actions := actions if {
	result == "require_revision"
	actions := object.get(input, "required_actions_hint", ["revise_candidate_and_reevaluate"])
} else := actions if {
	result == "block_and_escalate"
	actions := ["escalate_to_authorized_human", "record_audit_event"]
} else := []

# --- Hard blocks (must be evaluated before emitting/finalizing a proposal) ---

deny_block contains msg if {
	input.proposal_kind == "containment"
	input.context.rollback_documented != true
	msg := "R5: containment proposal blocked - rollback must be documented before proposal"
}

deny_block contains msg if {
	input.proposal_kind == "containment"
	input.context.target_ambiguous == true
	msg := "R2/R4: containment proposal blocked - target is ambiguous; escalate with knowns/missing"
}

deny_block contains msg if {
	input.proposal_kind == "containment"
	input.context.data_sufficient == false
	msg := "R4: containment proposal blocked - insufficient data for actionable proposal; escalate"
}

deny_block contains msg if {
	input.proposal_kind == "query_execution"
	input.context.has_explicit_approval_record != true
	msg := "R2/R7: query execution proposal blocked - explicit linked approval record required"
}

deny_block contains msg if {
	input.proposal_kind == "query_proposal"
	input.context.query_parameters_complete == false
	msg := "R7: query proposal requires revision/blocking metadata - time window, data scope, and cost estimate must be present or explicitly justified with escalation"
}

# Explicit execution attempts by agent are never allowed
deny_block contains msg if {
	object.get(input.candidate, "execution_requested", false) == true
	msg := "R2: automatic or agent-executed destructive/action execution is forbidden"
}

result := "block_and_escalate" if {
	count(deny_block) > 0
}

reasons := msgs if {
	count(deny_block) > 0
	msgs := [m | some m in deny_block]
}

# --- Revisions (non-blocking but must be corrected before final proposal) ---

revision contains msg if {
	count(deny_block) == 0
	input.proposal_kind == "containment"
	object.get(input.context, "has_false_positive_alternative", false) != true
	msg := "R4/spec: proposal should include alternative hypothesis including false positive"
}

result := "require_revision" if {
	count(deny_block) == 0
	count(revision) > 0
}

reasons := msgs if {
	count(deny_block) == 0
	count(revision) > 0
	msgs := [m | some m in revision]
}

# --- Allow proposal emission/finalization (still not execution) ---

result := "allow_proposal" if {
	count(deny_block) == 0
	count(revision) == 0
}

reasons := ["policy checks passed for proposal emission (execution still requires separate explicit approval where applicable)"] if {
	result == "allow_proposal"
}
