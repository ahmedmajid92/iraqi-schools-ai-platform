"""
Adaptive quiz engine with gamification for computer lab.
Features: adaptive difficulty, timer support, points/badges, streaks.
"""
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


def load_question_bank(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Badge definitions
BADGES = {
    "first_correct": {
        "id": "first_correct",
        "name": "البداية الصحيحة",
        "icon": "🎯",
        "description": "أجبت على أول سؤال بشكل صحيح"
    },
    "streak_3": {
        "id": "streak_3",
        "name": "سلسلة 3",
        "icon": "🔥",
        "description": "أجبت على 3 أسئلة متتالية صحيحة"
    },
    "streak_5": {
        "id": "streak_5",
        "name": "سلسلة 5",
        "icon": "⚡",
        "description": "أجبت على 5 أسئلة متتالية صحيحة"
    },
    "streak_10": {
        "id": "streak_10",
        "name": "أسطوري",
        "icon": "🏆",
        "description": "أجبت على 10 أسئلة متتالية صحيحة"
    },
    "fast_answer": {
        "id": "fast_answer",
        "name": "البرق",
        "icon": "⚡",
        "description": "أجبت في أقل من 5 ثواني"
    },
    "perfect_10": {
        "id": "perfect_10",
        "name": "عشرة من عشرة",
        "icon": "💯",
        "description": "أجبت على 10 أسئلة صحيحة"
    },
    "level_3": {
        "id": "level_3",
        "name": "المستوى المتقدم",
        "icon": "🌟",
        "description": "وصلت للمستوى 3"
    },
    "half_Century": {
        "id": "half_century",
        "name": "نصف المئة",
        "icon": "🎖️",
        "description": "حصلت على 50 نقطة"
    }
}


class AdaptiveQuizEngine:
    """
    Adaptive quiz with gamification:
    - Difficulty adjusts based on performance
    - Timer per question (10-20s)
    - Points, streaks, badges
    - No repeated questions in same session
    """
    
    def __init__(self, bank: List[Dict]):
        self.bank = bank

    def _level_from_score(self, score: int) -> int:
        """Calculate difficulty level from cumulative score."""
        lvl = 2 + (score // 2)
        return max(1, min(3, lvl))

    def _get_timer_seconds(self, question: Dict) -> int:
        """Get timer seconds for question (default based on level)."""
        if "timer_seconds" in question:
            return question["timer_seconds"]
        # Default timer based on level
        level = question.get("level", 2)
        return {1: 12, 2: 15, 3: 18}.get(level, 15)

    def next_question(self, state: Dict) -> Optional[Dict]:
        """Get next question based on current state."""
        asked = set(state.get("asked_ids", []))
        score = int(state.get("score", 0))
        lvl = self._level_from_score(score)

        state["level"] = lvl

        # Try to get question at current level
        candidates = [q for q in self.bank if q.get("level") == lvl and q.get("id") not in asked]
        
        if not candidates:
            # Fallback: try adjacent levels
            for adj_lvl in [lvl - 1, lvl + 1]:
                if 1 <= adj_lvl <= 3:
                    candidates = [q for q in self.bank if q.get("level") == adj_lvl and q.get("id") not in asked]
                    if candidates:
                        break
        
        if not candidates:
            # Final fallback: any unasked
            candidates = [q for q in self.bank if q.get("id") not in asked]

        if not candidates:
            return None

        q = random.choice(candidates)

        # Store asked id
        state.setdefault("asked_ids", [])
        state["asked_ids"].append(q["id"])

        # Return question with timer but without revealing answer
        return {
            "id": q["id"],
            "level": q["level"],
            "topic": q.get("topic", ""),
            "prompt": q["prompt"],
            "choices": q["choices"],
            "timer_seconds": self._get_timer_seconds(q)
        }

    def apply_answer(
        self, 
        state: Dict, 
        qid: str, 
        chosen_index: int,
        time_taken_seconds: Optional[float] = None
    ) -> Tuple[Dict, Dict]:
        """
        Process answer and update state with gamification.
        
        Returns:
            Tuple of (feedback_dict, new_state)
        """
        q = next((x for x in self.bank if x.get("id") == qid), None)
        if not q:
            return {"ok": False, "message": "سؤال غير موجود."}, state

        correct_index = int(q["answer_index"])
        correct = (chosen_index == correct_index)
        timer_seconds = self._get_timer_seconds(q)
        
        # Check if answer was within time limit
        timed_out = False
        if time_taken_seconds is not None and time_taken_seconds > timer_seconds:
            timed_out = True
            correct = False  # Timeout counts as wrong

        # Update counters
        state["total"] = int(state.get("total", 0)) + 1
        
        # Points calculation
        base_points = {1: 10, 2: 15, 3: 20}.get(q.get("level", 2), 15)
        earned_points = 0
        
        # Track streaks
        current_streak = int(state.get("current_streak", 0))
        best_streak = int(state.get("best_streak", 0))
        
        # Badges earned this round
        new_badges = []
        existing_badges = state.get("badges", [])
        
        if correct:
            state["correct"] = int(state.get("correct", 0)) + 1
            state["score"] = int(state.get("score", 0)) + 1
            
            # Calculate points with bonuses
            earned_points = base_points
            
            # Time bonus (faster = more points)
            if time_taken_seconds is not None and time_taken_seconds < timer_seconds * 0.5:
                earned_points += 5  # Speed bonus
                
            # Streak bonus
            current_streak += 1
            if current_streak >= 3:
                earned_points += current_streak * 2  # Streak multiplier
            
            state["current_streak"] = current_streak
            state["best_streak"] = max(best_streak, current_streak)
            
            # Check for badges
            if state["correct"] == 1 and "first_correct" not in existing_badges:
                new_badges.append(BADGES["first_correct"])
                existing_badges.append("first_correct")
            
            if current_streak == 3 and "streak_3" not in existing_badges:
                new_badges.append(BADGES["streak_3"])
                existing_badges.append("streak_3")
            
            if current_streak == 5 and "streak_5" not in existing_badges:
                new_badges.append(BADGES["streak_5"])
                existing_badges.append("streak_5")
            
            if current_streak == 10 and "streak_10" not in existing_badges:
                new_badges.append(BADGES["streak_10"])
                existing_badges.append("streak_10")
            
            if time_taken_seconds and time_taken_seconds < 5 and "fast_answer" not in existing_badges:
                new_badges.append(BADGES["fast_answer"])
                existing_badges.append("fast_answer")
            
            if state["correct"] == 10 and "perfect_10" not in existing_badges:
                new_badges.append(BADGES["perfect_10"])
                existing_badges.append("perfect_10")
        else:
            state["score"] = int(state.get("score", 0)) - 1
            state["current_streak"] = 0  # Reset streak
        
        # Update total points
        state["points"] = int(state.get("points", 0)) + earned_points
        
        # Check point milestones
        if state["points"] >= 50 and "half_century" not in existing_badges:
            new_badges.append(BADGES["half_Century"])
            existing_badges.append("half_century")
        
        # Level badge
        new_level = self._level_from_score(int(state.get("score", 0)))
        state["level"] = new_level
        if new_level == 3 and "level_3" not in existing_badges:
            new_badges.append(BADGES["level_3"])
            existing_badges.append("level_3")
        
        state["badges"] = existing_badges

        # Build feedback
        if timed_out:
            tip = "⏰ انتهى الوقت! حاول أن تكون أسرع في المرة القادمة."
        elif correct:
            tips = [
                "أحسنت! 🎉",
                "ممتاز! استمر! 💪",
                "رائع! أنت متألق! ⭐",
                "إجابة صحيحة! 🏆"
            ]
            tip = random.choice(tips)
            if earned_points > base_points:
                tip += f" (+{earned_points} نقطة مع البونص!)"
            else:
                tip += f" (+{earned_points} نقطة)"
        else:
            tip = "لا بأس — اقرأ الشرح ثم حاول مجددًا. 📚"

        feedback = {
            "correct": correct,
            "timed_out": timed_out,
            "correct_index": correct_index,
            "explanation": q.get("explanation", ""),
            "tip": tip,
            "points_earned": earned_points,
            "current_streak": state.get("current_streak", 0),
            "new_badges": new_badges
        }
        
        return feedback, state


def get_initial_state() -> Dict:
    """Get initial state for a new quiz session."""
    return {
        "asked_ids": [],
        "score": 0,
        "correct": 0,
        "total": 0,
        "level": 2,
        "points": 0,
        "current_streak": 0,
        "best_streak": 0,
        "badges": []
    }
