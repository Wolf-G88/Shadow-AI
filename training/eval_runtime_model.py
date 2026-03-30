"""
Quick runtime evaluator for SILS checkpoints.

Loads a trained runtime checkpoint through SILSBackend and prints responses
for a few representative prompts.
"""

from pathlib import Path
import argparse
import json
import re
import sys
from typing import Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.sils_backend import SILSBackend


DEFAULT_PROMPTS = [
    "hey what all can shadow do 4 me pls",
    "what all can shadow do for me",
    "my name is wolf king",
    "im building a private ai assistant called shadow",
    "what is my name",
    "yo read this docx n summarize it real quick",
    "run ls -la for me",
    "delete everything in that drive",
    "be short direct and no fluff",
]


def normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def safe_console_text(text: str, limit: int = 200) -> str:
    preview = (text or "")[:limit]
    encoding = sys.stdout.encoding or "utf-8"
    return preview.encode(encoding, errors="replace").decode(encoding, errors="replace")


def load_cases(path: Path) -> List[Dict]:
    cases = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                cases.append(json.loads(line))
    return cases


def score_case(case: Dict, predicted_intent: Optional[Dict], response: str) -> Dict:
    normalized_response = normalize_text(response)
    expected_intent = case.get("expected_intent")
    required_keywords = [normalize_text(keyword) for keyword in case.get("required_keywords", []) if keyword]
    forbidden_keywords = [normalize_text(keyword) for keyword in case.get("forbidden_keywords", []) if keyword]

    intent_ok = True
    predicted_name = None
    if expected_intent:
        predicted_name = predicted_intent["name"] if predicted_intent else None
        intent_ok = predicted_name == expected_intent

    required_hits = [keyword for keyword in required_keywords if keyword in normalized_response]
    required_ok = len(required_hits) == len(required_keywords)

    forbidden_hits = [keyword for keyword in forbidden_keywords if keyword and keyword in normalized_response]
    forbidden_ok = len(forbidden_hits) == 0

    passed = intent_ok and required_ok and forbidden_ok
    return {
        "passed": passed,
        "intent_ok": intent_ok,
        "required_ok": required_ok,
        "forbidden_ok": forbidden_ok,
        "predicted_intent": predicted_name,
        "required_hits": required_hits,
        "forbidden_hits": forbidden_hits,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate a runtime SILS checkpoint")
    parser.add_argument("--model", type=str, required=True, help="Path to final_model.pt")
    parser.add_argument("--tokenizer", type=str, default=None, help="Path to tokenizer_metadata.json")
    parser.add_argument("--config", type=str, default=None, help="Path to sils_config.json")
    parser.add_argument("--cases", type=str, default=None, help="Path to JSONL benchmark cases")
    parser.add_argument("--max-new-tokens", type=int, default=24, help="Max generated tokens")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
    args = parser.parse_args()

    model_path = Path(args.model)
    tokenizer_path = Path(args.tokenizer) if args.tokenizer else model_path.with_name("tokenizer_metadata.json")
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = Path(__file__).parent.parent / "config" / "sils_config.json"

    backend = SILSBackend(
        config_path=str(config_path),
        model_path=str(model_path),
        tokenizer_path=str(tokenizer_path),
        user_id="default",
    )

    print("=" * 72)
    print("Runtime SILS Evaluation")
    print("=" * 72)
    print(f"Model: {model_path}")
    print(f"Tokenizer: {tokenizer_path}")
    print(f"Available: {backend.is_available()}")
    print()

    if args.cases:
        case_path = Path(args.cases)
        cases = load_cases(case_path)
        print(f"Cases: {case_path} ({len(cases)} total)")
        print()

        passed = 0
        intent_passed = 0
        response_passed = 0
        for index, case in enumerate(cases, start=1):
            prompt = case["prompt"]
            expected_intent = case.get("expected_intent")
            print(f"Case {index}: {case.get('id', f'case-{index}')}")
            print(f"Difficulty: {case.get('difficulty', 'unknown')}")
            print(f"Prompt: {safe_console_text(prompt)}")
            predicted_intent = backend.predict_intent(prompt)
            if predicted_intent:
                print(
                    f"Predicted intent: {predicted_intent['name']} "
                    f"({predicted_intent['confidence']:.2f})"
                )
            response = backend.generate(
                prompt,
                max_new_tokens=args.max_new_tokens,
                temperature=args.temperature,
            )
            print(f"Response: {safe_console_text(response)}")
            score = score_case(case, predicted_intent, response)
            if score["intent_ok"]:
                intent_passed += 1
            if score["required_ok"] and score["forbidden_ok"]:
                response_passed += 1
            if score["passed"]:
                passed += 1
            print(
                "Result: "
                f"pass={score['passed']} | intent_ok={score['intent_ok']} | "
                f"required_ok={score['required_ok']} | forbidden_ok={score['forbidden_ok']}"
            )
            if expected_intent:
                print(f"Expected intent: {expected_intent}")
            if case.get("required_keywords"):
                print(f"Required keywords: {', '.join(case['required_keywords'])}")
            if score["forbidden_hits"]:
                print(f"Forbidden hits: {', '.join(score['forbidden_hits'])}")
            print("-" * 72)

        print("Summary")
        print("-" * 72)
        print(f"Overall pass: {passed}/{len(cases)}")
        print(f"Intent pass: {intent_passed}/{len(cases)}")
        print(f"Response pass: {response_passed}/{len(cases)}")
    else:
        for prompt in DEFAULT_PROMPTS:
            print(f"Prompt: {safe_console_text(prompt)}")
            response = backend.generate(
                prompt,
                max_new_tokens=args.max_new_tokens,
                temperature=args.temperature,
            )
            print(f"Response: {safe_console_text(response)}")
            print("-" * 72)


if __name__ == "__main__":
    main()
