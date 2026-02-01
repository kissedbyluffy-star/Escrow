from __future__ import annotations

import random
from dataclasses import dataclass

EMOJIS = ["🍕", "🍔", "🌮", "🍣"]


@dataclass(frozen=True)
class CaptchaChallenge:
    correct: str
    options: list[str]


def generate_challenge() -> CaptchaChallenge:
    correct = random.choice(EMOJIS)
    options = EMOJIS.copy()
    random.shuffle(options)
    return CaptchaChallenge(correct=correct, options=options)
