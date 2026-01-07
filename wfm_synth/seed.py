from __future__ import annotations
import os
import time
import secrets
import random
from dataclasses import dataclass

@dataclass
class SeedContext:
    seed: int

def derive_seed(seed_mode: str = "random", seed: int | None = None) -> SeedContext:
    if seed_mode == "fixed":
        if seed is None:
            raise ValueError("seed_mode=fixed requires seed")
        return SeedContext(seed=int(seed))

    # random mode: entropy from time + secrets + PID
    entropy = (
        int(time.time() * 1000)
        ^ os.getpid()
        ^ secrets.randbits(64)
    )
    return SeedContext(seed=entropy & 0x7FFFFFFF)

def rng(seed: int) -> random.Random:
    r = random.Random()
    r.seed(seed)
    return r
