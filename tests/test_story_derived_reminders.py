from backend.app.models.care_plan import CarePlan, CarePlanReminder
from backend.app.services.story_playback import ReminderAgent, StoryAgent


def test_story_activities_are_explicit_and_do_not_infer_care_tasks():
    activities = StoryAgent("jasmine_morning").activities()
    activity_ids = {activity.activity_id for activity in activities}

    assert "jasmine_flowers" in activity_ids
    assert "cooking_and_meals" in activity_ids
    assert "walking" in activity_ids
    assert "garden_care" in activity_ids
    assert "drink_water" not in activity_ids
    assert "take_medicine" not in activity_ids
    assert all(activity.source == "story" for activity in activities)


def test_care_plan_can_supply_water_and_medicine_without_changing_story():
    care_plan = CarePlan(
        patient_id="P001",
        reminders=[
            CarePlanReminder(
                reminder_id="med_morning",
                patient_id="P001",
                task="Take morning medicine",
                reminder_type="medicine",
                time="08:00",
            ),
            CarePlanReminder(
                reminder_id="water_morning",
                patient_id="P001",
                task="Drink water",
                reminder_type="water",
                time="09:00",
            ),
        ],
    )
    agent = ReminderAgent(reminders={}, care_plan=care_plan)

    assert [item.reminder_type for item in agent.care_plan_reminders()] == ["medicine", "water"]
    assert agent.after_video("jasmine_01") is None
    assert all(item.source == "care_plan" for item in agent.care_plan_reminders())
