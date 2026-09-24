from ..data.narrations import NARRATIONS
from ..models.beat import StoryBeat
from ..models.story import Story
from story.scene_loader import load_scenes

STORIES: list[Story] = [
    Story(
        id="jasmine_morning",
        title="The Jasmine Morning",
        prompt="Show Lakshmi's jasmine morning memory, including watering the plant and making a flower garland.",
        description=(
            "Lakshmi's quiet morning ritual of opening the door, carrying the brass pot, "
            "tending the jasmine plant, collecting flowers, and making a garland."
        ),
        beats=[
            StoryBeat(
                id="jasmine_01",
                story_id="jasmine_morning",
                sequence=1,
                image_path="01_jasmine_morning/jasmine_01_door.jpg",
                action="Lakshmi bends down, closes the wooden back door, and returns naturally to standing.",
                motion="Lakshmi bends toward the door, reaches for it, gently pulls it closed, and slowly straightens back up.",
                camera="static",
                motion_sequence=[
                    "Lakshmi naturally bends forward toward the door and lowers her upper body",
                    "Lakshmi reaches toward the door, grasps it, and gently pulls it closed on its hinges",
                    "The door finishes closing, then Lakshmi slowly straightens back up to a natural standing position",
                ],
                motion_constraints=["walking"],
                narration=NARRATIONS["jasmine_01"]["opening"],
            ),
            StoryBeat(
                id="jasmine_02",
                story_id="jasmine_morning",
                sequence=2,
                image_path="01_jasmine_morning/jasmine_02_water_pot.jpg",
                action="Lakshmi fills the small brass pot halfway at the tap.",
                motion="Lakshmi lifts the brass pot, turns the tap slowly, and lets the water fill the pot to about halfway.",
                camera="static",
                motion_sequence=[
                    "Lakshmi lifts the brass pot with both hands",
                    "Lakshmi turns the tap and water begins to fill the pot gradually",
                    "Lakshmi stops when the pot is about halfway full and holds it steady",
                ],
                narration=NARRATIONS["jasmine_02"]["opening"],
            ),
            StoryBeat(
                id="jasmine_03",
                story_id="jasmine_morning",
                sequence=3,
                image_path="01_jasmine_morning/jasmine_03_walk_to_jasmine.jpg",
                action="Lakshmi carries the brass pot toward the jasmine plant.",
                motion="Lakshmi carefully carries the half-filled pot with both hands and walks toward the jasmine plant.",
                camera="static",
                motion_sequence=[
                    "Lakshmi balances the brass pot with both hands",
                    "Lakshmi takes a steady step forward while carrying it",
                    "Lakshmi continues walking naturally toward the jasmine plant with the pot held securely",
                ],
                narration=NARRATIONS["jasmine_03"]["opening"],
            ),
            StoryBeat(
                id="jasmine_04",
                story_id="jasmine_morning",
                sequence=4,
                image_path="01_jasmine_morning/jasmine_04_picking_flowers.jpg",
                action="Lakshmi selects flowers that opened during the night.",
                motion="Lakshmi bends toward the jasmine plant, gently touches an opened flower, and twists it away from the stem. She repeats the motion slowly.",
                camera="static",
                motion_sequence=[
                    "Lakshmi bends her torso forward toward the jasmine vine",
                    "Lakshmi gently touches a fully opened flower and twists it from the stem",
                    "Lakshmi lifts the flower carefully and holds it in her hand as the motion settles",
                ],
                narration=NARRATIONS["jasmine_04"]["opening"],
            ),
            StoryBeat(
                id="jasmine_05",
                story_id="jasmine_morning",
                sequence=5,
                image_path="01_jasmine_morning/jasmine_05_sorting_flowers.jpg",
                action="Lakshmi threads the jasmine flowers into a long garland.",
                motion="Lakshmi separates the flowers, handles the white thread carefully, and pushes the flowers onto it one by one.",
                camera="static",
                motion_sequence=[
                    "Lakshmi holds the thread in one hand and positions the first flower",
                    "Lakshmi threads the flower carefully through the strand one by one",
                    "Lakshmi continues adding flowers in a smooth sequence to complete the garland",
                ],
                narration=NARRATIONS["jasmine_05"]["opening"],
            ),
            StoryBeat(
                id="jasmine_06",
                story_id="jasmine_morning",
                sequence=6,
                image_path="01_jasmine_morning/jasmine_06_preparing_thread.jpg",
                action="Lakshmi prepares the white thread for the jasmine garland.",
                motion="Lakshmi measures the white thread, holds it taut, and prepares it carefully beside the flowers.",
                camera="static",
                motion_sequence=[
                    "Lakshmi gathers the white thread and holds it carefully between both hands",
                    "Lakshmi measures and straightens the thread beside the flowers",
                    "Lakshmi settles the thread into position ready to make the garland",
                ],
                narration=NARRATIONS["jasmine_06"]["opening"],
            ),
            StoryBeat(
                id="jasmine_07",
                story_id="jasmine_morning",
                sequence=7,
                image_path="01_jasmine_morning/jasmine_07_making_garland.jpg",
                action="Lakshmi continues threading jasmine flowers into the garland.",
                motion="Lakshmi adds the flowers one by one and gently gathers the growing garland in her hands.",
                camera="static",
                motion_sequence=[
                    "Lakshmi positions another jasmine flower against the thread",
                    "Lakshmi pushes the flower onto the thread with a gentle steady movement",
                    "Lakshmi gathers the growing garland neatly in her hands",
                ],
                narration=NARRATIONS["jasmine_07"]["opening"],
            ),
            StoryBeat(
                id="jasmine_08",
                story_id="jasmine_morning",
                sequence=8,
                image_path="01_jasmine_morning/jasmine_08_finished_morning.jpg",
                action="Lakshmi finishes the jasmine garland and rests with the completed morning ritual.",
                motion="Lakshmi lifts the finished garland, looks at it with quiet satisfaction, and lets it rest gently in her hands.",
                camera="static",
                motion_sequence=[
                    "Lakshmi lifts the completed jasmine garland carefully",
                    "Lakshmi looks at the finished flowers with a calm satisfied expression",
                    "Lakshmi lowers the garland gently and settles into a peaceful final pose",
                ],
                narration=NARRATIONS["jasmine_08"]["opening"],
            ),
        ],
    ),
    Story(
        id="mango_tree",
        title="The Mango Tree",
        prompt="Show Lakshmi's childhood mango tree memory with climbing, tasting mangoes, and sharing with her father.",
        description=(
            "A childhood summer memory of Lakshmi choosing a mango, climbing the mango tree, and sharing it with her father."
        ),
        beats=[
            StoryBeat(
                id="mango_01",
                story_id="mango_tree",
                sequence=1,
                image_path="02_Mango/mango_01_arrival.jpg",
                action="Lakshmi quietly enters the kitchen and chooses the largest mango.",
                motion="Lakshmi approaches the cloth bag, opens it, examines the mangoes, and gently presses the largest mango with her thumb.",
                camera="static",
                motion_sequence=[
                    "Lakshmi reaches toward the cloth bag with a steady hand",
                    "Lakshmi opens the bag and inspects the mangoes one by one",
                    "Lakshmi settles on the largest mango and gently presses it with her thumb",
                ],
                narration=NARRATIONS["mango_01"]["opening"],
            ),
            StoryBeat(
                id="mango_02",
                story_id="mango_tree",
                sequence=2,
                image_path="02_Mango/mango_02_largest_mango.jpg",
                action="Lakshmi carries the mango outside toward the mango tree.",
                motion="Lakshmi carries the mango and runs lightly toward the tree.",
                camera="static",
                motion_sequence=[
                    "Lakshmi lifts the mango carefully in her hand",
                    "Lakshmi begins moving forward toward the tree with a light run",
                    "Lakshmi continues running naturally while keeping the mango secure in her grip",
                ],
                narration=NARRATIONS["mango_02"]["opening"],
            ),
            StoryBeat(
                id="mango_03",
                story_id="mango_tree",
                sequence=3,
                image_path="02_Mango/mango_03_running_to_tree.jpg",
                action="Lakshmi climbs the mango tree and reaches her favorite branch.",
                motion="Lakshmi places one foot against the trunk, grips the branch above her, and carefully pulls herself upward.",
                camera="static",
                motion_sequence=[
                    "Lakshmi plants one foot against the trunk and reaches upward",
                    "Lakshmi grips the branch and pulls her body upward in a controlled climb",
                    "Lakshmi settles onto her favorite branch and steadies her position",
                ],
                narration=NARRATIONS["mango_03"]["opening"],
            ),
            StoryBeat(
                id="mango_04",
                story_id="mango_tree",
                sequence=4,
                image_path="02_Mango/mango_04_climbing_tree.jpg",
                action="Lakshmi sits on the branch and eats the mango.",
                motion="Lakshmi rests the mango in her lap, wipes it against her dress, bites into it, and reacts naturally to the juice.",
                camera="static",
                motion_sequence=[
                    "Lakshmi settles the mango in her lap and holds it steady",
                    "Lakshmi wipes the mango against her dress and bites into it naturally",
                    "Lakshmi reacts to the sweet juice while remaining seated comfortably on the branch",
                ],
                narration=NARRATIONS["mango_04"]["opening"],
            ),
            StoryBeat(
                id="mango_05",
                story_id="mango_tree",
                sequence=5,
                image_path="02_Mango/mango_05_eating_mango.jpg",
                action="Her father joins her and cuts the mango with his pocket knife.",
                motion="Her father carefully cuts the mango and sprinkles salt and chilli powder over the pieces before handing Lakshmi the largest piece.",
                camera="static",
                motion_sequence=[
                    "Her father leans in and raises the pocket knife toward the mango",
                    "Her father cuts the mango cleanly and sprinkles salt and chilli powder onto the pieces",
                    "Her father offers Lakshmi the largest piece while the motion settles into a calm shared moment",
                ],
                narration=NARRATIONS["mango_05"]["opening"],
            ),
        ],
    ),
    Story(
        id="rainy_day_kitchen",
        title="The Rainy-Day Kitchen",
        prompt="Show Lakshmi's rainy-day kitchen memory of cooking with mustard, curry leaves, garlic, and an iron pan.",
        description=(
            "A monsoon kitchen memory filled with rain, mustard seeds, curry leaves, garlic, and Lakshmi tasting her mother's food."
        ),
        beats=[
            StoryBeat(
                id="rain_01",
                story_id="rainy_day_kitchen",
                sequence=1,
                image_path="03_rainy_day_kitchen/rain_01_monsoon_arrives.jpg",
                action="Lakshmi sits near the kitchen door and watches the monsoon rain.",
                motion="Rain falls steadily outside while Lakshmi watches quietly from the kitchen doorway.",
                camera="static",
                motion_sequence=[
                    "Lakshmi turns her head gently toward the rain beyond the doorway",
                    "Lakshmi settles into a still listening posture while the rain continues",
                    "Lakshmi remains quietly attentive as the monsoon rain falls steadily outside",
                ],
                narration=NARRATIONS["rain_01"]["opening"],
            ),
            StoryBeat(
                id="rain_02",
                story_id="rainy_day_kitchen",
                sequence=2,
                image_path="03_rainy_day_kitchen/rain_02_iron_pan_oil.jpg",
                action="Her mother heats oil and adds mustard seeds to the iron pan.",
                motion="Oil heats in the pan and mustard seeds are added carefully.",
                camera="static",
                motion_sequence=[
                    "Her mother lowers the pan and brings the oil to a warm shimmer",
                    "Her mother pours in mustard seeds steadily as they begin to crackle",
                    "The seeds settle into the oil while the pan remains stable and hot",
                ],
                narration=NARRATIONS["rain_02"]["opening"],
            ),
            StoryBeat(
                id="rain_03",
                story_id="rainy_day_kitchen",
                sequence=3,
                image_path="03_rainy_day_kitchen/rain_03_mustard_curry_leaves.jpg",
                action="Curry leaves are added to the hot oil.",
                motion="The curry leaves enter the pan and immediately sizzle in the hot oil.",
                camera="static",
                motion_sequence=[
                    "Her mother reaches in with the curry leaves and drops them into the oil",
                    "The leaves sizzle immediately and curl gently in the heat",
                    "The pan settles as the curry leaves continue to fry in the hot oil",
                ],
                narration=NARRATIONS["rain_03"]["opening"],
            ),
            StoryBeat(
                id="rain_04",
                story_id="rainy_day_kitchen",
                sequence=4,
                image_path="03_rainy_day_kitchen/rain_05_peeling_garlic.jpg",
                action="Lakshmi peels and crushes garlic on the wooden board.",
                motion="Lakshmi presses each garlic clove with the flat side of the knife and removes the skin.",
                camera="static",
                motion_sequence=[
                    "Lakshmi presses the garlic clove against the board with the flat side of the knife",
                    "Lakshmi peels away the skin in a steady motion",
                    "Lakshmi continues crushing the garlic cleanly on the board",
                ],
                narration=NARRATIONS["rain_04"]["opening"],
            ),
            StoryBeat(
                id="rain_05",
                story_id="rainy_day_kitchen",
                sequence=5,
                image_path="03_rainy_day_kitchen/rain_07_tasting_bowl.jpg",
                action="Lakshmi tastes the food and decides whether more salt is needed.",
                motion="Her mother cools a small portion, Lakshmi tastes it, considers the flavor, and gestures that more salt is needed.",
                camera="static",
                motion_sequence=[
                    "Her mother offers a spoonful of warm food for Lakshmi to taste",
                    "Lakshmi tastes it and considers the flavor with a small thoughtful expression",
                    "Lakshmi gestures that more salt is needed and the moment settles naturally",
                ],
                narration=NARRATIONS["rain_05"]["opening"],
            ),
        ],
    ),
    Story(
        id="school_morning",
        title="The School Morning",
        prompt="Show Lakshmi's school morning memory of walking to school, crossing the bridge, and stopping at the tea shop.",
        description=(
            "Lakshmi and Radha's daily walk to school through the temple, bridge, tea shop, and soft dirt road."
        ),
        beats=[
            StoryBeat(
                id="school_01",
                story_id="school_morning",
                sequence=1,
                image_path="04_school_morning/school_01_morning_route.jpg",
                action="Lakshmi and Radha begin their morning walk to school.",
                motion="The girls begin walking together along their familiar route.",
                camera="static",
                motion_sequence=[
                    "Lakshmi and Radha begin walking together from a natural standing pose",
                    "They take synchronized steps forward along the familiar route",
                    "They continue walking smoothly together without breaking stride",
                ],
                narration=NARRATIONS["school_01"]["opening"],
            ),
            StoryBeat(
                id="school_02",
                story_id="school_morning",
                sequence=2,
                image_path="04_school_morning/school_02_old_temple.jpg",
                action="Lakshmi and Radha pass the old temple and cross the small bridge.",
                motion="The girls continue walking and cross the bridge naturally.",
                camera="static",
                motion_sequence=[
                    "Lakshmi and Radha continue walking forward toward the temple and bridge",
                    "They step onto the bridge and cross it in a steady rhythm",
                    "They finish the crossing and keep moving smoothly on the other side",
                ],
                narration=NARRATIONS["school_02"]["opening"],
            ),
            StoryBeat(
                id="school_03",
                story_id="school_morning",
                sequence=3,
                image_path="04_school_morning/school_03_small_bridge.jpg",
                action="The girls stop beside the tea shop and take their pieces of jaggery.",
                motion="They approach the counter and each takes one small piece of jaggery.",
                camera="static",
                motion_sequence=[
                    "Lakshmi and Radha walk up to the tea shop counter together",
                    "They stop in place and each reaches to take a piece of jaggery",
                    "They hold the jaggery naturally and settle into a brief still pose",
                ],
                narration=NARRATIONS["school_03"]["opening"],
            ),
            StoryBeat(
                id="school_04",
                story_id="school_morning",
                sequence=4,
                image_path="04_school_morning/school_04_tea_shop_jaggery.jpg",
                action="Lakshmi removes her shoes and walks barefoot on the soft dirt.",
                motion="Lakshmi removes her shoes and walks slowly barefoot along the soft dirt.",
                camera="static",
                motion_sequence=[
                    "Lakshmi bends slightly to remove one shoe and then the other",
                    "She steps onto the soft dirt and begins walking barefoot in a natural rhythm",
                    "She continues walking forward across the dirt without sudden changes in direction",
                ],
                narration=NARRATIONS["school_04"]["opening"],
            ),
            StoryBeat(
                id="school_05",
                story_id="school_morning",
                sequence=5,
                image_path="04_school_morning/school_05_barefoot_walk.jpg",
                action="Lakshmi and Radha arrive at the school gate.",
                motion="The girls reach the school entrance and walk through the gate.",
                camera="static",
                motion_sequence=[
                    "Lakshmi and Radha walk forward toward the gate together",
                    "They step through the entrance in a continuous sequence",
                    "They complete the transition and continue walking naturally beyond the gate",
                ],
                narration=NARRATIONS["school_05"]["opening"],
            ),
        ],
    ),
    Story(
        id="railway_station",
        title="The Railway Station",
        prompt="Show Lakshmi's railway station memory of fixing a sandal, picking up a book, and waiting for the train.",
        description=(
            "The rainy railway-station memory where Lakshmi meets the young man who helps repair her sandal."
        ),
        beats=[
            StoryBeat(
                id="railway_01",
                story_id="railway_station",
                sequence=1,
                image_path="05_railway_station/station_01_rain_arrival.jpg",
                action="Lakshmi waits beneath the railway station roof during heavy rain.",
                motion="Rain falls heavily beyond the roof while Lakshmi waits holding her books.",
                camera="static",
                motion_sequence=[
                    "Lakshmi holds her books and remains still beneath the roof as rain falls",
                    "She shifts her posture slightly to stay comfortable while waiting",
                    "She remains under the shelter, attentive to the rain without sudden movement",
                ],
                narration=NARRATIONS["railway_01"]["opening"],
            ),
            StoryBeat(
                id="railway_02",
                story_id="railway_station",
                sequence=2,
                image_path="05_railway_station/station_02_broken_sandal.jpg",
                action="Lakshmi struggles with her broken sandal strap.",
                motion="Lakshmi bends down and tries to reconnect the broken strap.",
                camera="static",
                motion_sequence=[
                    "Lakshmi bends forward toward the sandal to inspect the broken strap",
                    "She gathers the strap and attempts to reconnect it with careful hand movement",
                    "She holds the sandal in place while the repair attempt settles into a focused pose",
                ],
                narration=NARRATIONS["railway_02"]["opening"],
            ),
            StoryBeat(
                id="railway_03",
                story_id="railway_station",
                sequence=3,
                image_path="05_railway_station/station_05_tying_sandal.jpg",
                action="A young man crouches down and ties the sandal with string.",
                motion="The young man takes a piece of string from his bag and carefully ties the sandal strap.",
                camera="static",
                motion_sequence=[
                    "The young man crouches down beside Lakshmi and reaches into his bag",
                    "He pulls out a string and begins tying the sandal strap in a careful sequence",
                    "He completes the knot and settles the sandal into place without abrupt motion",
                ],
                narration=NARRATIONS["railway_03"]["opening"],
            ),
            StoryBeat(
                id="railway_04",
                story_id="railway_station",
                sequence=4,
                image_path="05_railway_station/station_06_thank_you_book_falls.jpg",
                action="The young man picks up Lakshmi's fallen book.",
                motion="The book falls, the young man notices it, bends down, and picks it up for Lakshmi.",
                camera="static",
                motion_sequence=[
                    "The book slips from Lakshmi's grasp and falls toward the ground",
                    "The young man notices, bends down, and reaches for it",
                    "He lifts the book and hands it back to Lakshmi in one continuous motion",
                ],
                narration=NARRATIONS["railway_04"]["opening"],
            ),
            StoryBeat(
                id="railway_05",
                story_id="railway_station",
                sequence=5,
                image_path="05_railway_station/station_08_train_arrives.jpg",
                action="His train arrives and Lakshmi watches him leave.",
                motion="The train arrives, the young man leaves with his suitcase, and Lakshmi watches as the train departs.",
                camera="static",
                motion_sequence=[
                    "The train approaches and the young man begins to gather his suitcase",
                    "He steps away and turns to leave while Lakshmi watches",
                    "The train departs and both figures remain in a natural final pose as the motion ends",
                ],
                narration=NARRATIONS["railway_05"]["opening"],
            ),
        ],
    ),
]


def _align_beats_to_scene_images() -> None:
    """Make every registered beat use the repository image for its scene sequence."""
    story_ids = {
        "The Jasmine Morning": "jasmine_morning",
        "The Mango Tree": "mango_tree",
        "The Rainy-Day Kitchen": "rainy_day_kitchen",
        "The School Morning": "school_morning",
        "The Railway Station": "railway_station",
    }
    prefixes = {
        "jasmine_morning": "jasmine",
        "mango_tree": "mango",
        "rainy_day_kitchen": "rain",
        "school_morning": "school",
        "railway_station": "railway",
    }
    scenes_by_story: dict[str, list] = {story_id: [] for story_id in story_ids.values()}
    for scene in load_scenes():
        story_id = story_ids.get(scene.story_reference)
        if story_id and scene.image_asset:
            scenes_by_story[story_id].append(scene)

    for story in STORIES:
        existing = {beat.sequence: beat for beat in story.beats}
        aligned: list[StoryBeat] = []
        for scene in sorted(scenes_by_story.get(story.id, []), key=lambda item: item.sequence):
            beat = existing.get(scene.sequence)
            if beat is None:
                beat = StoryBeat(
                    id=f"{prefixes[story.id]}_{scene.sequence:02d}",
                    story_id=story.id,
                    sequence=scene.sequence,
                    image_path=scene.image_asset.filename,
                    action=scene.story_section,
                    motion=scene.narrative_summary,
                    camera="static",
                    motion_sequence=[scene.narrative_summary],
                    narration=scene.narrative_summary,
                )
            else:
                beat.image_path = scene.image_asset.filename
            aligned.append(beat)
        story.beats = aligned


_align_beats_to_scene_images()


def get_story(story_id: str):
    return next((story for story in STORIES if story.id == story_id), None)


def get_all_stories():
    return STORIES
