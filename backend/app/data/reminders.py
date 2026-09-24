from ..models.reminder import BeatReminder, ReminderQuestion


JASMINE_MORNING_REMINDERS: dict[str, BeatReminder] = {
    "jasmine_03": BeatReminder(
        beat_id="jasmine_03",
        question=ReminderQuestion(
            question_id="jasmine_recall_door",
            prompt="What did Lakshmi do earlier with the door?",
            expected_concepts=["closed the door"],
            acceptable_answers=["closed the door", "shut the door", "pulled the door closed"],
            hint="Think about how Lakshmi began her morning at the doorway.",
        ),
    ),
    "jasmine_04": BeatReminder(
        beat_id="jasmine_04",
        question=ReminderQuestion(
            question_id="jasmine_recall_pot",
            prompt="What was Lakshmi carrying toward the jasmine plant?",
            expected_concepts=["brass pot"],
            acceptable_answers=["a brass pot", "the brass pot", "pot of water"],
            hint="It was a small container filled halfway with water.",
        ),
    ),
    "jasmine_05": BeatReminder(
        beat_id="jasmine_05",
        question=ReminderQuestion(
            question_id="jasmine_recall_sequence",
            type="recognition",
            prompt="What flower is Lakshmi using for the garland?",
            expected_concepts=["jasmine flowers"],
            acceptable_answers=[
                "jasmine",
                "jasmine flowers",
                "white flowers",
            ],
            hint="Look at the flowers in Lakshmi's hands.",
        ),
    ),
}
