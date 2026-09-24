"""
Beat narrations and interaction questions.

Each beat has:
  opening  — the memory narration read aloud before the question
  question — the open-ended prompt shown/spoken to the patient after the video
  question_by_language — same question in supported languages
"""

NARRATIONS: dict[str, dict] = {
    # ── Jasmine Morning ──────────────────────────────────────────────────────
    "jasmine_01": {
        "opening": "Every morning began quietly. I would open the wooden door at the back of the house and step outside before the day became busy.",
        "question": "What is Lakshmi doing at the door?",
        "question_by_language": {
            "en": "What is Lakshmi doing at the door?",
            "ta": "லக்ஷ்மி கதவில் என்ன செய்கிறாள்?",
            "hi": "लक्ष्मी दरवाज़े पर क्या कर रही है?",
            "te": "లక్ష్మి తలుపు దగ్గర ఏమి చేస్తోంది?",
            "kn": "ಲಕ್ಷ್ಮಿ ಬಾಗಿಲಿನ ಬಳಿ ಏನು ಮಾಡುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "jasmine_02": {
        "opening": "I usually walked barefoot. I liked the cool earth beneath my feet in those early morning hours.",
        "question": "What is Lakshmi filling at the tap?",
        "question_by_language": {
            "en": "What is Lakshmi filling at the tap?",
            "ta": "லக்ஷ்மி குழாயில் என்ன நிரப்புகிறாள்?",
            "hi": "लक्ष्मी नल पर क्या भर रही है?",
            "te": "లక్ష్మి కుళాయి దగ్గర ఏమి నింపుతోంది?",
            "kn": "ಲಕ್ಷ್ಮಿ ನಲ್ಲಿಯಲ್ಲಿ ಏನು ತುಂಬಿಸುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "jasmine_03": {
        "opening": "Beside the door was my brass pot. I would carry it to the tap and fill it only halfway, just enough to carry comfortably.",
        "question": "Where is Lakshmi carrying the pot?",
        "question_by_language": {
            "en": "Where is Lakshmi carrying the pot?",
            "ta": "லக்ஷ்மி பாத்திரத்தை எங்கே எடுத்துச் செல்கிறாள்?",
            "hi": "लक्ष्मी बर्तन कहाँ ले जा रही है?",
            "te": "లక్ష్మి కుండను ఎక్కడికి తీసుకెళ్తోంది?",
            "kn": "ಲಕ್ಷ್ಮಿ ಪಾತ್ರೆಯನ್ನು ಎಲ್ಲಿಗೆ ಒಯ್ಯುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "jasmine_04": {
        "opening": "Then I would walk to the jasmine plant and wait. I never hurried the flowers. I waited for the ones that had opened.",
        "question": "What flowers is Lakshmi collecting?",
        "question_by_language": {
            "en": "What flowers is Lakshmi collecting?",
            "ta": "லக்ஷ்மி என்ன பூக்களை சேகரிக்கிறாள்?",
            "hi": "लक्ष्मी कौन से फूल चुन रही है?",
            "te": "లక్ష్మి ఏ పువ్వులు సేకరిస్తోంది?",
            "kn": "ಲಕ್ಷ್ಮಿ ಯಾವ ಹೂವುಗಳನ್ನು ಆಯ್ಕೆ ಮಾಡುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "jasmine_05": {
        "opening": "I gathered the flowers into the corner of my sari and sat down with the white thread. One flower at a time, I made the garland.",
        "question": "What is Lakshmi making with the flowers?",
        "question_by_language": {
            "en": "What is Lakshmi making with the flowers?",
            "ta": "லக்ஷ்மி பூக்களால் என்ன செய்கிறாள்?",
            "hi": "लक्ष्मी फूलों से क्या बना रही है?",
            "te": "లక్ష్మి పువ్వులతో ఏమి చేస్తోంది?",
            "kn": "ಲಕ್ಷ್ಮಿ ಹೂವುಗಳಿಂದ ಏನು ಮಾಡುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "jasmine_06": {
        "opening": "I measured the white thread carefully and kept it ready beside the flowers. The morning felt calm and unhurried.",
        "question": "What is Lakshmi preparing beside the flowers?",
        "question_by_language": {
            "en": "What is Lakshmi preparing beside the flowers?",
            "hi": "लक्ष्मी फूलों के पास क्या तैयार कर रही है?",
            "te": "లక్ష్మి పువ్వుల పక్కన ఏమి సిద్ధం చేస్తోంది?",
            "ta": "லக்ஷ்மி பூக்களின் அருகில் எதைத் தயாரிக்கிறாள்?",
            "kn": "ಲಕ್ಷ್ಮಿ ಹೂವುಗಳ ಬಳಿ ಏನನ್ನು ಸಿದ್ಧಪಡಿಸುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "jasmine_07": {
        "opening": "Then I continued adding the flowers one by one. The small white blossoms slowly became a long, fragrant garland.",
        "question": "What is Lakshmi adding to the thread?",
        "question_by_language": {
            "en": "What is Lakshmi adding to the thread?",
            "hi": "लक्ष्मी धागे में क्या जोड़ रही है?",
            "te": "లక్ష్మి దారానికి ఏమి జోడిస్తోంది?",
            "ta": "லக்ஷ்மி நூலில் எதைச் சேர்க்கிறாள்?",
            "kn": "ಲಕ್ಷ್ಮಿ ದಾರಕ್ಕೆ ಏನನ್ನು ಸೇರಿಸುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "jasmine_08": {
        "opening": "When the garland was finished, I held it for a moment and admired the work. The quiet morning ritual was complete.",
        "question": "What has Lakshmi finished making?",
        "question_by_language": {
            "en": "What has Lakshmi finished making?",
            "hi": "लक्ष्मी ने क्या बनाकर पूरा किया है?",
            "te": "లక్ష్మి ఏమి తయారు చేయడం పూర్తి చేసింది?",
            "ta": "லக்ஷ்மி எதைச் செய்து முடித்திருக்கிறாள்?",
            "kn": "ಲಕ್ಷ್ಮಿ ಏನನ್ನು ತಯಾರಿಸಿ ಮುಗಿಸಿದ್ದಾಳೆ?",
        },
    },

    # ── Mango Tree ───────────────────────────────────────────────────────────
    "mango_01": {
        "opening": "Sometimes I would quietly enter the kitchen and look through the cloth bag. I always searched for the biggest mango.",
        "question": "What is Lakshmi looking for in the kitchen?",
        "question_by_language": {
            "en": "What is Lakshmi looking for in the kitchen?",
            "ta": "லக்ஷ்மி சமையலறையில் என்ன தேடுகிறாள்?",
            "hi": "लक्ष्मी रसोई में क्या ढूंढ रही है?",
            "te": "లక్ష్మి వంటగదిలో ఏమి వెతుకుతోంది?",
            "kn": "ಲಕ್ಷ್ಮಿ ಅಡುಗೆಮನೆಯಲ್ಲಿ ಏನು ಹುಡುಕುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "mango_02": {
        "opening": "Once I had chosen one, I would carry it outside and run straight to the mango tree.",
        "question": "Where is Lakshmi running with the mango?",
        "question_by_language": {
            "en": "Where is Lakshmi running with the mango?",
            "ta": "லக்ஷ்மி மாம்பழத்துடன் எங்கே ஓடுகிறாள்?",
            "hi": "लक्ष्मी आम लेकर कहाँ दौड़ रही है?",
            "te": "లక్ష్మి మామిడిపండుతో ఎక్కడికి పరుగెత్తుతోంది?",
            "kn": "ಲಕ್ಷ್ಮಿ ಮಾವಿನ ಹಣ್ಣಿನೊಂದಿಗೆ ಎಲ್ಲಿಗೆ ಓಡುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "mango_03": {
        "opening": "I knew that tree well. I could climb its trunk and settle myself comfortably on one of the branches.",
        "question": "What is Lakshmi climbing?",
        "question_by_language": {
            "en": "What is Lakshmi climbing?",
            "ta": "லக்ஷ்மி எதை ஏறுகிறாள்?",
            "hi": "लक्ष्मी क्या चढ़ रही है?",
            "te": "లక్ష్మి దేన్ని ఎక్కుతోంది?",
            "kn": "ಲಕ್ಷ್ಮಿ ಏನನ್ನು ಹತ್ತುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "mango_04": {
        "opening": "Sitting high in the tree, I would wipe the mango on my dress and take the first bite. Somehow, mangoes always tasted better up there.",
        "question": "What is Lakshmi eating on the branch?",
        "question_by_language": {
            "en": "What is Lakshmi eating on the branch?",
            "ta": "லக்ஷ்மி கிளையில் என்ன சாப்பிடுகிறாள்?",
            "hi": "लक्ष्मी डाल पर क्या खा रही है?",
            "te": "లక్ష్మి కొమ్మపై ఏమి తింటోంది?",
            "kn": "ಲಕ್ಷ್ಮಿ ಕೊಂಬೆಯ ಮೇಲೆ ಏನು ತಿನ್ನುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "mango_05": {
        "opening": "Sometimes my father would come and sit beside me. He would cut the mango with his little pocket knife and add salt and chilli.",
        "question": "What did her father add to the mango?",
        "question_by_language": {
            "en": "What did her father add to the mango?",
            "ta": "அவளுடைய அப்பா மாம்பழத்தில் என்ன சேர்த்தார்?",
            "hi": "उनके पिता ने आम में क्या मिलाया?",
            "te": "ఆమె తండ్రి మామిడిపండుకు ఏమి కలిపారు?",
            "kn": "ಅವಳ ತಂದೆ ಮಾವಿನ ಹಣ್ಣಿಗೆ ಏನು ಸೇರಿಸಿದರು?",
        },
    },

    # ── Rainy-Day Kitchen ────────────────────────────────────────────────────
    "rain_01": {
        "opening": "When the monsoon came, the whole kitchen seemed to listen to the rain. I would stand near the doorway and watch the water falling outside.",
        "question": "What is Lakshmi watching outside?",
        "question_by_language": {
            "en": "What is Lakshmi watching outside?",
            "ta": "லக்ஷ்மி வெளியே என்ன பார்க்கிறாள்?",
            "hi": "लक्ष्मी बाहर क्या देख रही है?",
            "te": "లక్ష్మి బయట ఏమి చూస్తోంది?",
            "kn": "ಲಕ್ಷ್ಮಿ ಹೊರಗೆ ಏನು ನೋಡುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "rain_02": {
        "opening": "Inside, my mother would place the iron pan on the stove and wait for it to become hot.",
        "question": "What is her mother heating on the stove?",
        "question_by_language": {
            "en": "What is her mother heating on the stove?",
            "ta": "அவளுடைய அம்மா அடுப்பில் என்ன சூடாக்குகிறாள்?",
            "hi": "उनकी माँ चूल्हे पर क्या गर्म कर रही है?",
            "te": "ఆమె తల్లి పొయ్యిపై ఏమి వేడి చేస్తోంది?",
            "kn": "ಅವಳ ತಾಯಿ ಒಲೆಯ ಮೇಲೆ ಏನು ಕಾಯಿಸುತ್ತಿದ್ದಾರೆ?",
        },
    },
    "rain_03": {
        "opening": "Then came the oil, the mustard seeds, and finally the curry leaves. The moment they touched the hot pan, the whole kitchen came alive.",
        "question": "What did her mother add to the hot oil?",
        "question_by_language": {
            "en": "What did her mother add to the hot oil?",
            "ta": "அவளுடைய அம்மா சூடான எண்ணெயில் என்ன சேர்த்தாள்?",
            "hi": "उनकी माँ ने गर्म तेल में क्या डाला?",
            "te": "ఆమె తల్లి వేడి నూనెలో ఏమి వేసింది?",
            "kn": "ಅವಳ ತಾಯಿ ಬಿಸಿ ಎಣ್ಣೆಗೆ ಏನು ಹಾಕಿದರು?",
        },
    },
    "rain_04": {
        "opening": "I would sit nearby peeling the garlic. Sometimes I crushed it with my hands while my mother continued cooking.",
        "question": "What is Lakshmi peeling on the board?",
        "question_by_language": {
            "en": "What is Lakshmi peeling on the board?",
            "ta": "லக்ஷ்மி பலகையில் என்ன உரிக்கிறாள்?",
            "hi": "लक्ष्मी बोर्ड पर क्या छील रही है?",
            "te": "లక్ష్మి బల్లపై ఏమి వలుస్తోంది?",
            "kn": "ಲಕ್ಷ್ಮಿ ಹಲಗೆಯ ಮೇಲೆ ಏನು ಸುಲಿಯುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "rain_05": {
        "opening": "When everything was ready, my mother would give me a small cooled portion to taste. I learned to tell her whether it needed a little more salt.",
        "question": "What is Lakshmi tasting from the bowl?",
        "question_by_language": {
            "en": "What is Lakshmi tasting from the bowl?",
            "ta": "லக்ஷ்மி கிண்ணத்திலிருந்து என்ன சுவைக்கிறாள்?",
            "hi": "लक्ष्मी कटोरे से क्या चख रही है?",
            "te": "లక్ష్మి గిన్నె నుండి ఏమి రుచి చూస్తోంది?",
            "kn": "ಲಕ್ಷ್ಮಿ ಬಟ್ಟಲಿನಿಂದ ಏನು ರುಚಿ ನೋಡುತ್ತಿದ್ದಾಳೆ?",
        },
    },

    # ── School Morning ───────────────────────────────────────────────────────
    "school_01": {
        "opening": "When I was about twelve, I walked to school with Radha. We knew the road so well that we hardly needed to think about where our feet were taking us.",
        "question": "Who is walking with Lakshmi to school?",
        "question_by_language": {
            "en": "Who is walking with Lakshmi to school?",
            "ta": "லக்ஷ்மியுடன் பள்ளிக்கு யார் நடக்கிறார்கள்?",
            "hi": "लक्ष्मी के साथ स्कूल कौन जा रहा है?",
            "te": "లక్ష్మితో పాఠశాలకు ఎవరు నడుస్తున్నారు?",
            "kn": "ಲಕ್ಷ್ಮಿಯೊಂದಿಗೆ ಶಾಲೆಗೆ ಯಾರು ನಡೆಯುತ್ತಿದ್ದಾರೆ?",
        },
    },
    "school_02": {
        "opening": "We passed the old temple, crossed the little bridge, and walked past the tea shop. The same places were part of our morning every day.",
        "question": "What did they cross on the way to school?",
        "question_by_language": {
            "en": "What did they cross on the way to school?",
            "ta": "பள்ளிக்கு வழியில் அவர்கள் என்ன கடந்தார்கள்?",
            "hi": "स्कूल के रास्ते में उन्होंने क्या पार किया?",
            "te": "పాఠశాలకు వెళ్ళే దారిలో వారు ఏమి దాటారు?",
            "kn": "ಶಾಲೆಗೆ ಹೋಗುವ ದಾರಿಯಲ್ಲಿ ಅವರು ಏನನ್ನು ದಾಟಿದರು?",
        },
    },
    "school_03": {
        "opening": "Sometimes we stopped for little pieces of jaggery. It was a small treat, but those little things made the walk to school special.",
        "question": "What sweet did they take from the tea shop?",
        "question_by_language": {
            "en": "What sweet did they take from the tea shop?",
            "ta": "அவர்கள் தேயிலைக் கடையிலிருந்து என்ன இனிப்பு எடுத்தார்கள்?",
            "hi": "उन्होंने चाय की दुकान से कौन सी मिठाई ली?",
            "te": "వారు టీ షాప్ నుండి ఏ తీపి తీసుకున్నారు?",
            "kn": "ಅವರು ಚಹಾ ಅಂಗಡಿಯಿಂದ ಯಾವ ಸಿಹಿ ತೆಗೆದುಕೊಂಡರು?",
        },
    },
    "school_04": {
        "opening": "I carried my books in a blue cloth bag, while Radha had a brown one. We carried everything we needed for the school day inside them.",
        "question": "What did Lakshmi remove before walking on the soft dirt?",
        "question_by_language": {
            "en": "What did Lakshmi remove before walking on the soft dirt?",
            "ta": "மென்மையான மண்ணில் நடப்பதற்கு முன் லக்ஷ்மி என்ன கழற்றினாள்?",
            "hi": "नरम मिट्टी पर चलने से पहले लक्ष्मी ने क्या उतारा?",
            "te": "మెత్తని మట్టిపై నడవడానికి ముందు లక్ష్మి ఏమి తీసింది?",
            "kn": "ಮೃದುವಾದ ಮಣ್ಣಿನ ಮೇಲೆ ನಡೆಯುವ ಮೊದಲು ಲಕ್ಷ್ಮಿ ಏನನ್ನು ತೆಗೆದಳು?",
        },
    },
    "school_05": {
        "opening": "Halfway to school, I would sometimes take off my shoes and walk barefoot on the soft dirt. I would put them back on before reaching the school gate.",
        "question": "Where did Lakshmi and Radha arrive at the end of their walk?",
        "question_by_language": {
            "en": "Where did Lakshmi and Radha arrive at the end of their walk?",
            "ta": "நடை முடிவில் லக்ஷ்மியும் ராதாவும் எங்கே வந்தார்கள்?",
            "hi": "चलने के अंत में लक्ष्मी और राधा कहाँ पहुँचीं?",
            "te": "నడక చివరలో లక్ష్మి మరియు రాధ ఎక్కడికి చేరుకున్నారు?",
            "kn": "ನಡಿಗೆಯ ಕೊನೆಯಲ್ಲಿ ಲಕ್ಷ್ಮಿ ಮತ್ತು ರಾಧಾ ಎಲ್ಲಿಗೆ ತಲುಪಿದರು?",
        },
    },

    # ── Railway Station ──────────────────────────────────────────────────────
    "railway_01": {
        "opening": "That day, the rain was heavy. I stood beneath the station roof holding my books and waited for the train.",
        "question": "What is Lakshmi holding while waiting at the station?",
        "question_by_language": {
            "en": "What is Lakshmi holding while waiting at the station?",
            "ta": "நிலையத்தில் காத்திருக்கும்போது லக்ஷ்மி என்ன வைத்திருக்கிறாள்?",
            "hi": "स्टेशन पर इंतज़ार करते समय लक्ष्मी क्या पकड़े हुए है?",
            "te": "స్టేషన్‌లో వేచి ఉన్నప్పుడు లక్ష్మి ఏమి పట్టుకుంది?",
            "kn": "ನಿಲ್ದಾಣದಲ್ಲಿ ಕಾಯುತ್ತಿರುವಾಗ ಲಕ್ಷ್ಮಿ ಏನನ್ನು ಹಿಡಿದಿದ್ದಾಳೆ?",
        },
    },
    "railway_02": {
        "opening": "One of my sandals had broken. I looked down at the loose strap, wondering how I would manage the rest of the journey.",
        "question": "What broke on Lakshmi's foot?",
        "question_by_language": {
            "en": "What broke on Lakshmi's foot?",
            "ta": "லக்ஷ்மியின் காலில் என்ன உடைந்தது?",
            "hi": "लक्ष्मी के पैर में क्या टूट गया?",
            "te": "లక్ష్మి పాదంలో ఏమి విరిగింది?",
            "kn": "ಲಕ್ಷ್ಮಿಯ ಕಾಲಿನಲ್ಲಿ ಏನು ಮುರಿಯಿತು?",
        },
    },
    "railway_03": {
        "opening": "A young man noticed it. He crouched down, took a piece of string, and carefully tied the sandal back together.",
        "question": "What did the young man use to fix the sandal?",
        "question_by_language": {
            "en": "What did the young man use to fix the sandal?",
            "ta": "இளைஞன் செருப்பை சரிசெய்ய என்ன பயன்படுத்தினான்?",
            "hi": "युवक ने चप्पल ठीक करने के लिए क्या इस्तेमाल किया?",
            "te": "యువకుడు చెప్పును సరిచేయడానికి ఏమి ఉపయోగించాడు?",
            "kn": "ಯುವಕ ಚಪ್ಪಲಿ ಸರಿಪಡಿಸಲು ಏನು ಬಳಸಿದ?",
        },
    },
    "railway_04": {
        "opening": "Then one of my books slipped from my hands. He picked it up and gave it back to me just as the announcement for the train came.",
        "question": "What did the young man pick up for Lakshmi?",
        "question_by_language": {
            "en": "What did the young man pick up for Lakshmi?",
            "ta": "இளைஞன் லக்ஷ்மிக்காக என்ன எடுத்தான்?",
            "hi": "युवक ने लक्ष्मी के लिए क्या उठाया?",
            "te": "యువకుడు లక్ష్మి కోసం ఏమి తీసుకున్నాడు?",
            "kn": "ಯುವಕ ಲಕ್ಷ್ಮಿಗಾಗಿ ಏನನ್ನು ಎತ್ತಿಕೊಂಡ?",
        },
    },
    "railway_05": {
        "opening": "The train arrived, and everything became noisy for a moment. He left with the crowd, and I watched the train disappear into the rain.",
        "question": "What did Lakshmi watch disappear into the rain?",
        "question_by_language": {
            "en": "What did Lakshmi watch disappear into the rain?",
            "ta": "மழையில் மறைவதை லக்ஷ்மி என்ன பார்த்தாள்?",
            "hi": "लक्ष्मी ने बारिश में क्या गायब होते देखा?",
            "te": "వర్షంలో మాయమవడాన్ని లక్ష్మి ఏమి చూసింది?",
            "kn": "ಮಳೆಯಲ್ಲಿ ಮರೆಯಾಗುವುದನ್ನು ಲಕ್ಷ್ಮಿ ಏನನ್ನು ನೋಡಿದಳು?",
        },
    },
    "mango_06": {
        "question": "Who came to the mango tree?",
        "question_by_language": {
            "en": "Who came to the mango tree?",
            "hi": "आम के पेड़ के पास कौन आया?",
            "te": "మామిడి చెట్టు దగ్గరకు ఎవరు వచ్చారు?",
            "ta": "மாமரத்திடம் யார் வந்தார்?",
            "kn": "ಮಾವಿನ ಮರದ ಬಳಿ ಯಾರು ಬಂದರು?",
        },
    },
    "mango_07": {
        "question": "What did her father sprinkle on the mango?",
        "question_by_language": {
            "en": "What did her father sprinkle on the mango?",
            "hi": "उसके पिता ने आम पर क्या छिड़का?",
            "te": "ఆమె తండ్రి మామిడిపై ఏమి చల్లారు?",
            "ta": "அவளுடைய அப்பா மாம்பழத்தின் மீது என்ன தூவினார்?",
            "kn": "ಅವಳ ತಂದೆ ಮಾವಿನ ಹಣ್ಣಿನ ಮೇಲೆ ಏನು ಚಿಮುಕಿಸಿದರು?",
        },
    },
    "mango_08": {
        "question": "Which piece of mango did Lakshmi receive?",
        "question_by_language": {
            "en": "Which piece of mango did Lakshmi receive?",
            "hi": "लक्ष्मी को आम का कौन सा टुकड़ा मिला?",
            "te": "లక్ష్మికి మామిడి పండు ముక్కల్లో ఏది దొరికింది?",
            "ta": "லக்ஷ்மிக்கு மாம்பழத்தின் எந்த துண்டு கிடைத்தது?",
            "kn": "ಲಕ್ಷ್ಮಿಗೆ ಮಾವಿನ ಹಣ್ಣಿನ ಯಾವ ತುಂಡು ಸಿಕ್ಕಿತು?",
        },
    },
    "rain_06": {
        "question": "What is Lakshmi smelling in the kitchen?",
        "question_by_language": {
            "en": "What is Lakshmi smelling in the kitchen?",
            "hi": "लक्ष्मी रसोई में किसकी खुशबू सूंघ रही है?",
            "te": "లక్ష్మి వంటగదిలో దేని వాసన చూస్తోంది?",
            "ta": "லக்ஷ்மி சமையலறையில் எதன் வாசனையை உணர்கிறாள்?",
            "kn": "ಲಕ್ಷ್ಮಿ ಅಡುಗೆಮನೆಯಲ್ಲಿ ಯಾವುದರ ವಾಸನೆಯನ್ನು ಅನುಭವಿಸುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "rain_07": {
        "question": "What is Lakshmi tasting from the small bowl?",
        "question_by_language": {
            "en": "What is Lakshmi tasting from the small bowl?",
            "hi": "लक्ष्मी छोटी कटोरी से क्या चख रही है?",
            "te": "లక్ష్మి చిన్న గిన్నె నుండి ఏమి రుచి చూస్తోంది?",
            "ta": "லக்ஷ்மி சிறிய கிண்ணத்திலிருந்து என்ன சுவைக்கிறாள்?",
            "kn": "ಲಕ್ಷ್ಮಿ ಸಣ್ಣ ಬಟ್ಟಲಿನಿಂದ ಏನು ರುಚಿ ನೋಡುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "rain_08": {
        "question": "What does the food need more of?",
        "question_by_language": {
            "en": "What does the food need more of?",
            "hi": "खाने में और किस चीज़ की ज़रूरत है?",
            "te": "ఆహారానికి ఇంకా ఏమి కావాలి?",
            "ta": "உணவுக்கு இன்னும் என்ன வேண்டும்?",
            "kn": "ಆಹಾರಕ್ಕೆ ಇನ್ನೇನು ಬೇಕು?",
        },
    },
    "school_06": {
        "question": "Where does Lakshmi sit in the classroom?",
        "question_by_language": {
            "en": "Where does Lakshmi sit in the classroom?",
            "hi": "लक्ष्मी कक्षा में कहाँ बैठती है?",
            "te": "లక్ష్మి తరగతి గదిలో ఎక్కడ కూర్చుంటుంది?",
            "ta": "லக்ஷ்மி வகுப்பறையில் எங்கே உட்கார்கிறாள்?",
            "kn": "ಲಕ್ಷ್ಮಿ ತರಗತಿಯಲ್ಲಿ ಎಲ್ಲಿ ಕುಳಿತುಕೊಳ್ಳುತ್ತಾಳೆ?",
        },
    },
    "school_07": {
        "question": "What is Lakshmi drawing in her notebook?",
        "question_by_language": {
            "en": "What is Lakshmi drawing in her notebook?",
            "hi": "लक्ष्मी अपनी कॉपी में क्या बना रही है?",
            "te": "లక్ష్మి తన నోటుబుక్‌లో ఏమి గీస్తోంది?",
            "ta": "லக்ஷ்மி தனது நோட்டுப் புத்தகத்தில் என்ன வரைகிறாள்?",
            "kn": "ಲಕ್ಷ್ಮಿ ತನ್ನ ನೋಟ್ ಪುಸ್ತಕದಲ್ಲಿ ಏನು ಚಿತ್ರಿಸುತ್ತಿದ್ದಾಳೆ?",
        },
    },
    "school_08": {
        "question": "What are Lakshmi and Radha sharing?",
        "question_by_language": {
            "en": "What are Lakshmi and Radha sharing?",
            "hi": "लक्ष्मी और राधा क्या बाँट रही हैं?",
            "te": "లక్ష్మి మరియు రాధా ఏమి పంచుకుంటున్నారు?",
            "ta": "லக்ஷ்மியும் ராதாவும் எதைப் பகிர்ந்து கொள்கிறார்கள்?",
            "kn": "ಲಕ್ಷ್ಮಿ ಮತ್ತು ರಾಧಾ ಏನನ್ನು ಹಂಚಿಕೊಳ್ಳುತ್ತಿದ್ದಾರೆ?",
        },
    },
    "school_09": {
        "question": "What do the girls share every day?",
        "question_by_language": {
            "en": "What do the girls share every day?",
            "hi": "लड़कियाँ हर दिन क्या बाँटती हैं?",
            "te": "ఆ అమ్మాయిలు ప్రతిరోజూ ఏమి పంచుకుంటారు?",
            "ta": "அந்தப் பெண்கள் தினமும் எதைப் பகிர்ந்து கொள்கிறார்கள்?",
            "kn": "ಆ ಹುಡುಗಿಯರು ಪ್ರತಿದಿನ ಏನನ್ನು ಹಂಚಿಕೊಳ್ಳುತ್ತಾರೆ?",
        },
    },
    "railway_06": {
        "question": "Where did Lakshmi meet the young man?",
        "question_by_language": {
            "en": "Where did Lakshmi meet the young man?",
            "hi": "लक्ष्मी उस युवक से कहाँ मिली?",
            "te": "లక్ష్మి ఆ యువకుడిని ఎక్కడ కలిసింది?",
            "ta": "லக்ஷ்மி அந்த இளைஞரை எங்கே சந்தித்தாள்?",
            "kn": "ಲಕ್ಷ್ಮಿ ಆ ಯುವಕನನ್ನು ಎಲ್ಲಿ ಭೇಟಿಯಾದಳು?",
        },
    },
    "railway_07": {
        "question": "Who helped Lakshmi at the station?",
        "question_by_language": {
            "en": "Who helped Lakshmi at the station?",
            "hi": "स्टेशन पर लक्ष्मी की मदद किसने की?",
            "te": "స్టేషన్‌లో లక్ష్మికి ఎవరు సహాయం చేశారు?",
            "ta": "நிலையத்தில் லக்ஷ்மிக்கு யார் உதவினார்?",
            "kn": "ನಿಲ್ದಾಣದಲ್ಲಿ ಲಕ್ಷ್ಮಿಗೆ ಯಾರು ಸಹಾಯ ಮಾಡಿದರು?",
        },
    },
    "railway_08": {
        "question": "What arrived at the station?",
        "question_by_language": {
            "en": "What arrived at the station?",
            "hi": "स्टेशन पर क्या आया?",
            "te": "స్టేషన్‌కు ఏమి వచ్చింది?",
            "ta": "நிலையத்திற்கு என்ன வந்தது?",
            "kn": "ನಿಲ್ದಾಣಕ್ಕೆ ಏನು ಬಂದಿತು?",
        },
    },
    "railway_09": {
        "question": "Where did this memory take place?",
        "question_by_language": {
            "en": "Where did this memory take place?",
            "hi": "यह याद कहाँ की है?",
            "te": "ఈ జ్ఞాపకం ఎక్కడ జరిగింది?",
            "ta": "இந்த நினைவு எங்கே நடந்தது?",
            "kn": "ಈ ನೆನಪು ಎಲ್ಲಿ ನಡೆಯಿತು?",
        },
    },
}
