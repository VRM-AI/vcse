"""Deterministic explanation renderers."""

from __future__ import annotations

from dataclasses import asdict

from vcse.explain.model import ExplanationResult, ProofTrace


class ExplanationRenderer:
    def render_text(self, trace: ProofTrace) -> str:
        title = f"{trace.result_subject} {trace.result_relation} {trace.result_object}."
        lines = [
            title,
            "",
            "Status:",
            f"- verification_status: {trace.verification_status}",
        ]
        if trace.proof_count > 0:
            lines.extend(["", "Reasoning path:"])
            proof_steps = [node for node in trace.nodes if node.node_type == "proof_step"]
            for index, node in enumerate(proof_steps, start=1):
                if node.subject and node.relation and node.object:
                    step_text = f"{node.subject} {node.relation} {node.object}."
                else:
                    step_text = f"{node.message}."
                suffix = ""
                if node.pack_id or node.claim_id:
                    suffix = f" [{node.pack_id or 'unknown'}:{node.claim_id or 'unknown'}]"
                lines.append(f"{index}. {step_text}{suffix}")
            if trace.verification_status == "VERIFIED":
                lines.extend(["", "Therefore:", f"{trace.result_subject} {trace.result_relation} {trace.result_object}."])
        elif trace.verification_status == "UNVERIFIED":
            lines.extend(
                [
                    "",
                    "Reason:",
                    "- no proof trace is available",
                    "- result must not be treated as verified",
                ]
            )

        support_lines = _support_lines(trace)
        if support_lines:
            lines.extend(["", "Support:", *support_lines])

        return "\n".join(lines)

    def render_json(self, trace: ProofTrace) -> dict:
        payload = asdict(trace)
        payload["nodes"] = [asdict(node) for node in trace.nodes]
        return payload

    def render_result_json(self, result: ExplanationResult) -> dict:
        return {
            "status": result.status,
            "trace_count": result.trace_count,
            "traces": [self.render_json(trace) for trace in result.traces],
        }


def _support_lines(trace: ProofTrace) -> list[str]:
    lines: list[str] = []
    primary = next((node for node in trace.nodes if node.node_type in {"explicit_claim", "inferred_claim"}), None)
    if primary is not None:
        if primary.claim_id is not None:
            lines.append(f"- claim_id: {primary.claim_id}")
        if primary.pack_id is not None:
            lines.append(f"- pack: {primary.pack_id}")
        if primary.trust_tier is not None:
            lines.append(f"- trust_tier: {primary.trust_tier}")
        if primary.lifecycle_status is not None:
            lines.append(f"- lifecycle_status: {primary.lifecycle_status}")
    provenance_nodes = [node for node in trace.nodes if node.node_type == "provenance" and node.provenance is not None]
    if provenance_nodes:
        for node in provenance_nodes:
            lines.append(f"- provenance: {node.provenance}")
    elif trace.proof_count == 0:
        lines.append("- no proof trace available")
    return lines
