"""Controlled local Laya configuration ablations; no sentence rules or paid API.

Runs the pre-existing development split only unless --all-cases is explicit.
The result records every score and prepared-input hash for backend parity checks.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

LONG_INSTRUCTION = "Based on the recent conversation, has the latest speaker made a new, complete request that calls for the listener to respond now?"
YES = "The current utterance asks the listener to answer, explain or elaborate, including an imperative or a contextual follow-up."
NO = "The current utterance is an answer, statement, acknowledgement, reported speech, cancelled request or unfinished thought. Previous requests are background only."
DEFINITIONS = {
    "baseline_noul": {"type": "noul", "instructions": LONG_INSTRUCTION, "criteria": {"true": YES, "false": NO}},
    "same_named_choice": {"type": "choice", "instructions": LONG_INSTRUCTION, "criteria": {"respond": YES, "wait": NO}},
    "same_neutral_choice": {"type": "choice", "instructions": LONG_INSTRUCTION, "criteria": {"A": YES, "B": NO}},
    "same_neutral_reversed": {"type": "choice", "instructions": LONG_INSTRUCTION, "criteria": {"B": NO, "A": YES}},
    "short_noul": {"type": "noul", "instructions": "Does the current message ask the listener to respond?"},
    "short_neutral_choice": {"type": "choice", "instructions": "Does the current message ask the listener to respond?", "criteria": {"A": "Yes, the listener should respond now.", "B": "No, the listener should wait."}},
    "intent_neutral_choice": {"type": "choice", "instructions": "Classify the conversational intent of the current message.", "criteria": {"A": "A complete question or request for the listener to provide information.", "B": "A statement, answer, acknowledgement, reported request, cancelled request or unfinished thought."}},
    "chinese_neutral_choice": {"type": "choice", "instructions": "根据对话背景，当前这句话是否已经形成需要听者回应的新请求？", "criteria": {"A": "是，应当开始回答当前的新请求。", "B": "否，应当继续等待，无需回答。"}},
}

def positive(answer):
    if answer["type"] == "noul":
        return answer["noul"]
    probs = answer["probabilities"]
    return probs.get("A", probs.get("respond"))

def states(case):
    turns = case["context"]["recentTurns"]
    current = {"previous_turns": turns, "current_speaker": case["context"]["currentSpeaker"], "current_utterance": case["text"]}
    clean = {"history": [{"speaker": t["speaker"], "text": t["text"]} for t in turns], "current_message": case["text"]}
    return {
        "app_compact": json.dumps(current, ensure_ascii=False, separators=(",", ":")),
        "app_default_json": current,
        "simple_json": clean,
        "plain_context": "Previous conversation (background only):\n" + "\n".join(t["speaker"] + ": " + t["text"] for t in turns) + "\nCurrent message:\n" + case["text"],
        "raw_current_control": case["text"],
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["mlx", "torch"], default="mlx")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=Path, default=Path(__file__).with_name("laya_rolling_samples.json"))
    parser.add_argument("--all-cases", action="store_true")
    parser.add_argument("--parity-only", action="store_true")
    parser.add_argument("--label-audit", action="store_true")
    parser.add_argument("--candidate-only", action="store_true")
    args = parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", USE_TF="0", TOKENIZERS_PARALLELISM="false")
    sys.path.insert(0, str(args.source))
    if args.backend == "mlx":
        import laya_mlx as library
        agent = library.load(args.model, dtype=args.dtype)
    else:
        import laya as library
        agent = library.load(str(args.model), device="mps")
    cases = json.loads(args.samples.read_text())
    if not args.all_cases:
        cases = [c for c in cases if c["split"] == "development"]
    if not cases:
        raise ValueError("No selected cases; an empty evaluation is not a passing run")
    questions = dict(DEFINITIONS)
    if args.label_audit:
        questions = {
            "noul_neutral_labels": {"type":"noul", "instructions":LONG_INSTRUCTION, "criteria":{"false":NO,"true":YES}, "labels":{"false":"B","true":"A"}},
            "noul_action_labels": {"type":"noul", "instructions":LONG_INSTRUCTION, "criteria":{"false":NO,"true":YES}, "labels":{"false":"wait","true":"respond"}},
            "chinese_intent": {"type":"choice", "instructions":"当前说话者的这句话是什么意图？", "criteria":{"A":"向听者提问、请求信息或要求说明。", "B":"陈述、回答、确认、转述、撤回请求或尚未说完。"}},
            "short_request": {"type":"noul", "instructions":"Is the speaker asking the listener for information?"},
        }
    if args.parity_only:
        questions = {k: questions[k] for k in ["baseline_noul", "same_neutral_choice", "short_neutral_choice"]}
    if args.candidate_only:
        questions = {"baseline_noul": DEFINITIONS["baseline_noul"]}
    rows = []
    for case in cases:
        inputs = states(case)
        if args.parity_only:
            inputs = {"app_compact": inputs["app_compact"]}
        if args.candidate_only:
            inputs = {k:inputs[k] for k in ["app_compact", "plain_context"]}
        for name, state in inputs.items():
            result = agent.predict(state, questions)
            if args.backend == "mlx":
                prepared, _ = agent.prepare(state, questions)
            else:
                from laya.common import QTYPES, build_sequence
                prepared = []
                for definition in questions.values():
                    internal = agent._to_internal(definition)
                    ids, markers = build_sequence(agent.tok, state, internal, agent.cfg["max_len"], agent.cfg["head_max_len"])
                    prepared.append({"ids":ids,"markers":markers,"qtype":QTYPES[internal["t"]]})
            prepared_hashes = {key:hashlib.sha256(json.dumps({k:item[k] for k in ("ids","markers","qtype")},sort_keys=True).encode()).hexdigest()
                               for key,item in zip(questions, prepared)}
            lengths = {key:len(item["ids"]) for key,item in zip(questions, prepared)}
            for task, answer in result["answers"].items():
                rows.append({"id":case["id"], "split":case["split"], "expected":case["respond"],
                             "format":name, "task":task, "score":positive(answer),
                             "input_tokens":lengths[task],
                             "prepared_sha256":prepared_hashes[task]})
    controls = []
    control_questions = {
        "department": {"type":"choice", "instructions":"Which team should handle this request?", "criteria":{"billing":"invoices, payments, refunds", "technical":"bugs and outages", "sales":"pricing"}},
        "refund": {"type":"noul", "instructions":"Does the sender ask for money back?"}}
    for body in ["I was charged twice, please refund me.", "发票被重复扣款，请退款。", "The application keeps crashing.", "应用打不开，一直闪退。"]:
        controls.append({"state":{"body":body}, "answers":agent.predict({"body":body},control_questions)["answers"]})
    summaries = []
    for fmt in sorted({r["format"] for r in rows}):
        for task in questions:
            selected = [r for r in rows if r["task"]==task and r["format"]==fmt]
            for threshold in [0.5,0.8]:
                miss = sum(r["expected"] and r["score"]<threshold for r in selected)
                false = sum(not r["expected"] and r["score"]>=threshold for r in selected)
                summaries.append({"format":fmt,"task":task,"threshold":threshold,"passed":len(selected)-miss-false,"total":len(selected),"missed":miss,"false":false})
    report = {"backend":args.backend,"source":str(args.source),"model":str(args.model),"dtype":args.dtype if args.backend=="mlx" else "official_default",
              "samples_sha256":hashlib.sha256(args.samples.read_bytes()).hexdigest(),
              "definitions":questions,"rows":rows,"controls":controls,"summaries":summaries}
    if args.candidate_only:
        candidate_rows = [r for r in rows if r["format"]=="plain_context"]
        report["candidate_acceptance_passed"] = all((r["score"]>=0.8)==r["expected"] for r in candidate_rows)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    for r in sorted(summaries,key=lambda r:(-r["passed"],r["false"]))[:12]: print(json.dumps(r),flush=True)
    if args.candidate_only and not report["candidate_acceptance_passed"]:
        raise SystemExit(1)

if __name__ == "__main__": main()
