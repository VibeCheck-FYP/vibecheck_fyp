from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"


def q(name: str) -> str:
    return f"{{{BPMN_NS}}}{name}"


@dataclass
class FlowElement:
    kind: str
    elem_id: str
    name: str | None = None
    incoming: list[str] = field(default_factory=list)
    outgoing: list[str] = field(default_factory=list)


@dataclass
class SequenceFlow:
    flow_id: str
    source_ref: str
    target_ref: str
    name: str | None = None
    condition_expr: str | None = None


@dataclass
class ParsedProcess:
    process_id: str
    elements: dict[str, FlowElement]
    flows: dict[str, SequenceFlow]


def _text(elem: ET.Element | None) -> str | None:
    if elem is None or elem.text is None:
        return None
    t = elem.text.strip()
    return t or None


def _parse_condition_expression(flow_el: ET.Element) -> str | None:
    ce = flow_el.find(q("conditionExpression"))
    if ce is None:
        return None
    body = _text(ce)
    if body:
        return body
    lang_type = ce.attrib.get("{http://www.w3.org/1999/xlink}type") or ce.attrib.get("xsi:type")
    # Fallback: stringify attrib
    return ce.attrib.get("id")


def parse_bpmn_xml(xml_bytes: bytes | str, encoding: str = "utf-8") -> ParsedProcess:
    if isinstance(xml_bytes, str):
        root = ET.fromstring(xml_bytes.encode(encoding))
    else:
        root = ET.fromstring(xml_bytes)

    proc = root.find(q("process"))
    if proc is None:
        raise ValueError("No <process> found in BPMN definitions")

    process_id = proc.attrib.get("id", "anonymous")
    elements: dict[str, FlowElement] = {}
    flows: dict[str, SequenceFlow] = {}

    for child in proc:
        tag = child.tag
        if tag == q("sequenceFlow"):
            fid = child.attrib["id"]
            flows[fid] = SequenceFlow(
                flow_id=fid,
                source_ref=child.attrib["sourceRef"],
                target_ref=child.attrib["targetRef"],
                name=child.attrib.get("name"),
                condition_expr=_parse_condition_expression(child),
            )
            continue

        eid = child.attrib.get("id")
        if not eid:
            continue
        local = tag.split("}")[-1]
        fe = FlowElement(
            kind=local,
            elem_id=eid,
            name=child.attrib.get("name"),
            incoming=[t.text.strip() for t in child.findall(q("incoming")) if t.text],
            outgoing=[t.text.strip() for t in child.findall(q("outgoing")) if t.text],
        )
        elements[eid] = fe

    # Repair incomplete incoming/outgoing from sequence flows (exporters differ).
    for fl in flows.values():
        if fl.source_ref in elements and fl.flow_id not in elements[fl.source_ref].outgoing:
            elements[fl.source_ref].outgoing.append(fl.flow_id)
        if fl.target_ref in elements and fl.flow_id not in elements[fl.target_ref].incoming:
            elements[fl.target_ref].incoming.append(fl.flow_id)

    return ParsedProcess(process_id=process_id, elements=elements, flows=flows)


def _ap_begin(node_id: str) -> str:
    return f"begin_{node_id}"


def _ap_end(node_id: str) -> str:
    return f"end_{node_id}"


def _alive_guard(inner: str) -> str:
    """Alive discipline: invariants hold only while the process instance is alive."""
    return f"G(alive -> ({inner}))"


def _extract_gateway_decision_text(gw: FlowElement) -> str | None:
    if not gw.name:
        return None
    m = re.match(r"^\s*Decision:\s*(.+)\s*$", gw.name, flags=re.I | re.DOTALL)
    return m.group(1).strip() if m else None


def sequence_flow_guard_resolved(
    fl: SequenceFlow,
    sibling_flows_from_same_node: list[SequenceFlow],
    gw_decision: str | None,
) -> str:
    sorted_fl = sorted(sibling_flows_from_same_node, key=lambda f: f.flow_id)
    if fl.condition_expr:
        return fl.condition_expr
    unlabeled = [f for f in sorted_fl if not f.condition_expr]
    labeled = [f for f in sorted_fl if f.condition_expr]

    if gw_decision and len(unlabeled) == 2 and len(sorted_fl) == 2:
        return gw_decision if fl.flow_id == unlabeled[0].flow_id else f"!({gw_decision})"

    if len(unlabeled) == 1 and labeled:
        if fl in labeled:
            return fl.condition_expr or "true"
        disj = " | ".join(f"({x.condition_expr})" for x in labeled if x.condition_expr)
        return f"!({disj})" if disj else "true"

    if gw_decision:
        return gw_decision
    return "true"


def build_semantic_map(model: ParsedProcess) -> dict[str, Any]:
    tasks: dict[str, Any] = {}
    gateways: dict[str, Any] = {}
    events: dict[str, Any] = {}

    for eid, el in model.elements.items():
        if el.kind == "task":
            tasks[eid] = {
                "bpmn_id": eid,
                "kind": "task",
                "label": el.name or eid,
                "atomic_props": {"begin": _ap_begin(eid), "end": _ap_end(eid)},
            }
        elif el.kind == "exclusiveGateway":
            gateways[eid] = {
                "bpmn_id": eid,
                "kind": "exclusiveGateway",
                "label": el.name or eid,
                "decision_expression": _extract_gateway_decision_text(el),
                "atomic_props": {"evaluate": f"gw_{eid}_taken"},
            }
        elif el.kind in ("startEvent", "endEvent"):
            events[eid] = {
                "bpmn_id": eid,
                "kind": el.kind,
                "label": el.name or eid,
                "atomic_props": {"instant": _ap_begin(eid)},
            }

    outgoing_flows: dict[str, list[SequenceFlow]] = {}
    for fl in model.flows.values():
        outgoing_flows.setdefault(fl.source_ref, []).append(fl)

    flows_out: list[dict[str, Any]] = []
    for src, flist in outgoing_flows.items():
        src_el = model.elements.get(src)
        gw_expr = _extract_gateway_decision_text(src_el) if src_el and src_el.kind == "exclusiveGateway" else None
        for fl in flist:
            inferred = (
                sequence_flow_guard_resolved(fl, flist, gw_expr)
                if src_el and src_el.kind == "exclusiveGateway"
                else (fl.condition_expr or None)
            )
            flows_out.append(
                {
                    "flow_id": fl.flow_id,
                    "source_ref": fl.source_ref,
                    "target_ref": fl.target_ref,
                    "name": fl.name,
                    "condition_expression": inferred,
                }
            )

    return {
        "process_id": model.process_id,
        "tasks": tasks,
        "gateways": gateways,
        "events": events,
        "sequence_flows": flows_out,
    }


def build_m_spec(model: ParsedProcess, semantic: dict[str, Any]) -> dict[str, Any]:
    """Finite labeled transition system skeleton for Role C (guards as strings / AP names)."""
    nodes = sorted(model.elements.keys())
    transitions: list[dict[str, Any]] = []

    outgoing_flows: dict[str, list[SequenceFlow]] = {}
    for fl in model.flows.values():
        outgoing_flows.setdefault(fl.source_ref, []).append(fl)

    for src, flist in outgoing_flows.items():
        src_el = model.elements.get(src)
        gw_decision = _extract_gateway_decision_text(src_el) if src_el and src_el.kind == "exclusiveGateway" else None
        sorted_fl = sorted(flist, key=lambda f: f.flow_id)
        for fl in sorted_fl:
            if src_el and src_el.kind == "exclusiveGateway":
                guard = sequence_flow_guard_resolved(fl, flist, gw_decision)
            else:
                guard = fl.condition_expr or "true"

            transitions.append(
                {
                    "from": src,
                    "to": fl.target_ref,
                    "flow_id": fl.flow_id,
                    "guard": guard,
                    "labels": {"traverse": f"take_{fl.flow_id}"},
                }
            )

    starts = [eid for eid, el in model.elements.items() if el.kind == "startEvent"]
    ends = [eid for eid, el in model.elements.items() if el.kind == "endEvent"]

    return {
        "model": "M_spec",
        "process_id": model.process_id,
        "states": nodes,
        "initial_states": starts,
        "accepting_states": ends,
        "transitions": transitions,
        "semantic_ref": semantic["tasks"].keys(),
    }


def build_property_suite(model: ParsedProcess, semantic: dict[str, Any]) -> list[dict[str, Any]]:
    """Formal property suite P with Alive wrapping and criticality labels."""
    props: list[dict[str, Any]] = []

    def add(pid: str, category: str, inner: str, criticality: str, covered_ids: list[str]) -> None:
        props.append(
            {
                "id": pid,
                "category": category,
                "criticality": criticality,
                "formula": _alive_guard(inner),
                "inner": inner,
                "covered_element_ids": covered_ids,
            }
        )

    # Termination / liveness style (finite interpretation: reach end).
    end_nodes = [eid for eid, el in model.elements.items() if el.kind == "endEvent"]
    for eid in end_nodes:
        add(
            f"LIVE_TERM_{eid}",
            "liveness_termination",
            f"F({_ap_begin(eid)})",
            "P0",
            [eid],
        )

    # Alive semantics: once end event occurs, alive eventually false (process completes).
    for eid in end_nodes:
        add(
            f"ALIVE_STOP_{eid}",
            "alive_guard",
            f"({_ap_begin(eid)}) -> F(!alive)",
            "P0",
            [eid],
        )

    def precedence_antecedent(src_el: FlowElement, src_id: str) -> str:
        if src_el.kind == "task":
            return _ap_end(src_id)
        if src_el.kind == "exclusiveGateway":
            return _ap_begin(src_id)
        if src_el.kind == "startEvent":
            return _ap_begin(src_id)
        return _ap_begin(src_id)

    # Ordering along each sequenceFlow (Role B/C bridge uses begin/end task APs).
    for fl in model.flows.values():
        src, tgt = fl.source_ref, fl.target_ref
        src_el = model.elements.get(src)
        tgt_el = model.elements.get(tgt)
        if not src_el or not tgt_el:
            continue
        ant = precedence_antecedent(src_el, src)
        inner = f"({_ap_begin(tgt)}) -> ({ant})"
        add(f"ORD_{fl.flow_id}", "ordering", inner, "P1", [src, tgt, fl.flow_id])

    # XOR mutual exclusion: cannot complete both branches of the same split (single-token semantics).
    for eid, el in model.elements.items():
        if el.kind != "exclusiveGateway":
            continue
        outgoing = outgoing_flows_from(model, eid)
        tgts = [model.flows[fid].target_ref for fid in outgoing if fid in model.flows]
        task_tgts = [t for t in tgts if model.elements.get(t) and model.elements[t].kind == "task"]
        if len(task_tgts) >= 2:
            pairs = []
            for i in range(len(task_tgts)):
                for j in range(i + 1, len(task_tgts)):
                    a, b = task_tgts[i], task_tgts[j]
                    pairs.append(f"!(({_ap_end(a)}) & ({_ap_end(b)}))")
            if pairs:
                inner = "(" + ") & (".join(pairs) + ")"
                add(f"GW_XOR_MUTEX_{eid}", "gateway_invariant", inner, "P1", [eid] + task_tgts)

    # Quality: every declared task is eventually finished if begun (bounded work — strengthen later with fairness).
    for eid, el in model.elements.items():
        if el.kind != "task":
            continue
        inner = f"({_ap_begin(eid)}) -> F({_ap_end(eid)})"
        add(f"QUAL_FINISH_{eid}", "quality_bounded_task", inner, "P2", [eid])

    return props


def outgoing_flows_from(model: ParsedProcess, node_id: str) -> list[str]:
    return [fid for fid, fl in model.flows.items() if fl.source_ref == node_id]


def structural_coverage(model: ParsedProcess, props: list[dict[str, Any]]) -> dict[str, Any]:
    structural_ids: set[str] = set(model.elements.keys()) | set(model.flows.keys())
    covered: set[str] = set()
    for p in props:
        for cid in p.get("covered_element_ids", []):
            if cid in structural_ids:
                covered.add(cid)

    gamma_struct = len(covered) / len(structural_ids) if structural_ids else 1.0
    uncovered = sorted(structural_ids - covered)
    return {
        "gamma_struct": round(gamma_struct, 4),
        "counts": {
            "structural_elements": len(structural_ids),
            "covered_by_suite": len(covered),
            "uncovered": len(uncovered),
        },
        "uncovered_ids": uncovered,
    }


def simple_mutants(model: ParsedProcess) -> list[tuple[str, ParsedProcess]]:
    """Structural mutants for κ estimation (minimal illustration): drop one sequence flow."""
    mutants: list[tuple[str, ParsedProcess]] = []
    for fid in list(model.flows.keys()):
        flows2 = dict(model.flows)
        flows2.pop(fid)
        label = f"remove_flow:{fid}"
        mutants.append((label, ParsedProcess(model.process_id + "_mut", dict(model.elements), flows2)))
    return mutants


def mutant_kill_report(
    baseline_props: list[dict[str, Any]],
    baseline_gamma: float,
    mutants: list[tuple[str, ParsedProcess]],
) -> dict[str, Any]:
    """Kill = mutant changes coverage signature or property count (proxy until theorem prover hooks)."""
    kills = 0
    rows = []
    for label, m in mutants:
        sem = build_semantic_map(m)
        props_m = build_property_suite(m, sem)
        cov_m = structural_coverage(m, props_m)["gamma_struct"]
        killed = len(props_m) != len(baseline_props) or abs(cov_m - baseline_gamma) > 1e-6
        if killed:
            kills += 1
        rows.append({"mutant": label, "killed_proxy": killed, "gamma_struct_mutant": cov_m, "num_props": len(props_m)})

    kappa = kills / len(mutants) if mutants else 1.0
    return {
        "kappa_proxy": round(kappa, 4),
        "mutants_total": len(mutants),
        "mutants_killed_proxy": kills,
        "rows": rows[:20],
        "rows_truncated": len(rows) > 20,
    }


def run_role_a(path: Path | None = None, xml_text: str | None = None) -> dict[str, Any]:
    if path is not None:
        model = parse_bpmn_xml(path.read_bytes())
    elif xml_text is not None:
        model = parse_bpmn_xml(xml_text)
    else:
        raise ValueError("Provide path or xml_text")

    semantic = build_semantic_map(model)
    m_spec = build_m_spec(model, semantic)
    props = build_property_suite(model, semantic)
    cov = structural_coverage(model, props)
    mutants = simple_mutants(model)
    mut_rep = mutant_kill_report(props, cov["gamma_struct"], mutants)

    return {
        "semantic_bpmn_map": semantic,
        "M_spec": m_spec,
        "property_suite_P": props,
        "coverage_report": cov,
        "mutation_report": mut_rep,
    }


def main() -> None:
    here = Path(__file__).resolve().parent
    sample = here / "fixtures" / "sample_flow.bpmn"
    out = run_role_a(path=sample)
    print(json.dumps(out["semantic_bpmn_map"], indent=2))
    print("\n--- Property suite (sample) ---")
    for p in out["property_suite_P"][:8]:
        print(p["id"], p["criticality"], p["formula"])
    print("...")
    print("\n--- Coverage ---")
    print(json.dumps(out["coverage_report"], indent=2))
    print("\n--- Mutation proxy ---")
    print(json.dumps({k: out["mutation_report"][k] for k in ("kappa_proxy", "mutants_total")}, indent=2))


if __name__ == "__main__":
    main()
