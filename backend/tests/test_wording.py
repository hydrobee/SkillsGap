import pytest

from app.seed import SEED
from app.services.wording import third_person


@pytest.mark.parametrize("statement, expected", [
    ("I can build a feature from requirement to deployment on my own.",
     "Bella can build a feature from requirement to deployment on his/her own."),
    ("I often need help to debug my code.", "Bella often needs help to debug his/her code."),
    ("I apply input validation and access checks by default.",
     "Bella applies input validation and access checks by default."),
    ("I file and retrieve records accurately following the SOP.",
     "Bella files and retrieves records accurately following the SOP."),
    ("I often need to pass routine complaints to my supervisor.",
     "Bella often needs to pass routine complaints to his/her supervisor."),
    ("I struggle to use the LMS to run assessments.", "Bella struggles to use the LMS to run assessments."),
    ("I plan, test and deploy releases.", "Bella plans, tests and deploys releases."),
    ("I don't miss deadlines.", "Bella doesn't miss deadlines."),
    ("I'm comfortable presenting.", "Bella is comfortable presenting."),
    ("I ask for help when I am stuck.", "Bella asks for help when he/she is stuck."),
    ("I test my work myself.", "Bella tests his/her work himself/herself."),
    ("My reports are accurate.", "Bella's reports are accurate."),
    ("Colleagues ask me about I/O errors.", "Colleagues ask him/her about I/O errors."),
])
def test_third_person(statement, expected):
    assert third_person(statement, "Bella") == expected


def test_role_is_dropped_from_the_name():
    assert third_person("I can lead.", "Aiman (ICT Supervisor)") == "Aiman can lead."


def test_every_seeded_question_is_rewritten():
    for rows in SEED.values():
        for _, _, text, _ in rows:
            result = third_person(text, "Bella")
            assert result.startswith("Bella ") and " my " not in result
