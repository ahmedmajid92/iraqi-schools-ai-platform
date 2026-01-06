import json
import random
from typing import Dict, List, Optional

def load_question_bank(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

class AdaptiveQuizEngine:
    """
    Simple adaptive logic:
    - keep a 'score' that shifts difficulty
    - level = clamp(2 + score//2, 1..3)
    - avoid repeating asked questions
    """
    def __init__(self, bank: List[Dict]):
        self.bank = bank

    def _level_from_score(self, score: int) -> int:
        lvl = 2 + (score // 2)
        return max(1, min(3, lvl))

    def next_question(self, state: Dict) -> Optional[Dict]:
        asked = set(state.get("asked_ids", []))
        score = int(state.get("score", 0))
        lvl = self._level_from_score(score)

        state["level"] = lvl

        candidates = [q for q in self.bank if q.get("level") == lvl and q.get("id") not in asked]
        if not candidates:
            # fallback: any unasked
            candidates = [q for q in self.bank if q.get("id") not in asked]

        if not candidates:
            return None

        q = random.choice(candidates)

        # store asked id
        state.setdefault("asked_ids", [])
        state["asked_ids"].append(q["id"])

        # return question without revealing answer
        return {
            "id": q["id"],
            "level": q["level"],
            "topic": q.get("topic", ""),
            "prompt": q["prompt"],
            "choices": q["choices"]
        }

    def apply_answer(self, state: Dict, qid: str, chosen_index: int):
        q = next((x for x in self.bank if x.get("id") == qid), None)
        if not q:
            return {"ok": False, "message": "سؤال غير موجود."}, state

        correct_index = int(q["answer_index"])
        correct = (chosen_index == correct_index)

        # update counters
        state["total"] = int(state.get("total", 0)) + 1
        if correct:
            state["correct"] = int(state.get("correct", 0)) + 1
            state["score"] = int(state.get("score", 0)) + 1
        else:
            state["score"] = int(state.get("score", 0)) - 1

        state["level"] = self._level_from_score(int(state.get("score", 0)))

        feedback = {
            "correct": correct,
            "correct_index": correct_index,
            "explanation": q.get("explanation", ""),
            "tip": "أحسنت! لننتقل لسؤال آخر." if correct else "لا بأس—اقرأ الشرح ثم حاول مجددًا."
        }
        return feedback, state
