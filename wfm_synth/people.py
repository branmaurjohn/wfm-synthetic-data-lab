from __future__ import annotations
from dataclasses import dataclass
from typing import List
from faker import Faker
import random

@dataclass
class Person:
    personId: int
    full_name: str
    first_name: str
    last_name: str
    email: str

def generate_people(n: int, rng: random.Random, company_domain: str = "examplehealth.org") -> List[Person]:
    fake = Faker("en_US")
    # ensure different each run even if Python global seed differs
    fake.seed_instance(rng.randint(1, 2_000_000_000))

    people = []
    for i in range(n):
        first = fake.first_name()
        last = fake.last_name()
        full = f"{first} {last}"
        email = f"{first}.{last}{rng.randint(1,9999)}@{company_domain}".lower()
        people.append(Person(
            personId=10_000_000 + i,
            full_name=full,
            first_name=first,
            last_name=last,
            email=email
        ))
    return people
