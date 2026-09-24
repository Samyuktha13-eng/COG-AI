from ..models.story_activity import StoryDerivedActivity


LAKSHMI_STORY_ACTIVITIES: list[StoryDerivedActivity] = [
    StoryDerivedActivity(
        activity_id="jasmine_flowers",
        label="Jasmine and flower garland routine",
        evidence=["collects opened jasmine flowers", "threads flowers into garlands"],
        beat_ids=["jasmine_04", "jasmine_05"],
    ),
    StoryDerivedActivity(
        activity_id="cooking_and_meals",
        label="Cooking and preparing meals",
        evidence=["prepares food", "serves food", "makes breakfast and lunch"],
        beat_ids=["rain_02", "rain_03", "rain_05"],
    ),
    StoryDerivedActivity(
        activity_id="walking",
        label="Walking and going somewhere",
        evidence=["walks barefoot", "walks to school", "walks through the garden"],
        beat_ids=["jasmine_03", "school_01", "school_04", "school_05"],
    ),
    StoryDerivedActivity(
        activity_id="family_activities",
        label="Family activities",
        evidence=["raises a daughter", "shares meals", "spends time with family"],
        beat_ids=["mango_05", "school_03", "rain_05"],
    ),
    StoryDerivedActivity(
        activity_id="garden_care",
        label="Garden and plant care",
        evidence=["carries water toward the jasmine plant", "tends jasmine flowers"],
        beat_ids=["jasmine_02", "jasmine_03", "jasmine_04"],
    ),
    StoryDerivedActivity(
        activity_id="festival_preparation",
        label="Festival preparation",
        evidence=["draws rangoli", "arranges lamps", "prepares festival food"],
        beat_ids=[],
    ),
    StoryDerivedActivity(
        activity_id="mango_and_pickle_preparation",
        label="Mango and pickle preparation",
        evidence=["chooses mangoes", "cuts and seasons mango", "makes mango pickle"],
        beat_ids=["mango_01", "mango_04", "mango_05"],
    ),
    StoryDerivedActivity(
        activity_id="letter_and_brass_box",
        label="Letter and brass-box memories",
        evidence=["keeps a letter in a brass box"],
        beat_ids=[],
    ),
]
