"""Turns a first-person survey statement into one about the named staff member.

"I often need help to debug my code." -> "Bella often needs help to debug his/her code."
"""
import re

_MODALS = {"can", "cannot", "could", "may", "might", "must", "shall", "should", "will", "would"}
_UNCHANGED = _MODALS | {"was", "did", "had", "and", "or"}
_IRREGULAR = {"am": "is", "have": "has", "do": "does", "go": "goes"}
_CONTRACTIONS = {"m": "is", "ve": "has", "ll": "will", "d": "would"}
_PRONOUNS = {"myself": "himself/herself", "Myself": "Himself/Herself", "mine": "his/hers",
             "Mine": "His/Hers", "my": "his/her", "My": "His/Her", "me": "him/her", "Me": "Him/Her"}

# Listed explicitly because "-ly" also ends verbs such as apply, rely and comply.
_ADVERBS = ("often|always|never|sometimes|usually|rarely|seldom|also|still|regularly|frequently"
            "|generally|normally|typically|occasionally|consistently|actively|carefully"
            "|confidently|effectively|independently|routinely|proactively")
_WORD = r"[A-Za-z]+(?:['’][a-z]+)?"
_NEXT_VERB = rf"(?!(?:I|my|we|the|a|an|then|when|if|also|not)\b){_WORD}"
_SUBJECT = re.compile(
    r"(?<![\w/-])I(?:['’](?P<contraction>m|ve|ll|d))?(?![\w/-]|\.\w)"
    rf"(?P<adverbs>(?:\s+(?:{_ADVERBS})\b)*)"
    rf"(?P<verbs>\s+{_WORD}(?:(?:,\s*{_NEXT_VERB})*,?\s+(?:and|or)\s+{_NEXT_VERB})?)?"
)
_PRONOUN = re.compile(r"\b(?:myself|Myself|mine|Mine|my|My|me|Me)\b")


def _conjugate(verb: str) -> str:
    """Third-person singular of a present-tense verb; anything else is left alone."""
    if verb.replace("’", "'") == "don't":
        return "doesn't"
    if verb in _UNCHANGED or "'" in verb or "’" in verb:
        return verb
    if verb in _IRREGULAR:
        return _IRREGULAR[verb]
    if verb.endswith("ed") and not verb.endswith("eed"):
        return verb
    if re.search(r"(?:s|x|z|ch|sh|o)$", verb):
        return verb + "es"
    if re.search(r"[^aeiou]y$", verb):
        return verb[:-1] + "ies"
    return verb + "s"


def _conjugate_all(verbs: str) -> str:
    first = verbs.split()[0].rstrip(",").lower() if verbs.strip() else ""
    if first in _MODALS:
        return verbs
    return re.sub(_WORD, lambda m: _conjugate(m.group()), verbs)


def third_person(text: str, staff_name: str) -> str:
    # Display names can carry a role, e.g. "Aiman (ICT Supervisor)".
    name = re.sub(r"\s*\([^)]*\)\s*$", "", staff_name).strip() or staff_name
    named = text.startswith("My ")
    if named:
        text = f"{name}'s {text[3:]}"

    def subject(m: re.Match) -> str:
        nonlocal named
        if named:
            starts_sentence = m.string[:m.start()].rstrip()[-1:] in {"", ".", "!", "?"}
            who = "He/She" if starts_sentence else "he/she"
        else:
            who, named = name, True
        verbs = m["verbs"] or ""
        if m["contraction"]:
            return f"{who} {_CONTRACTIONS[m['contraction']]}{m['adverbs']}{verbs}"
        return f"{who}{m['adverbs']}{_conjugate_all(verbs)}"

    text = _SUBJECT.sub(subject, text)
    return _PRONOUN.sub(lambda m: _PRONOUNS[m.group()], text)
