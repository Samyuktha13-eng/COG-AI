import pytest

from voice.meaning import understand


@pytest.mark.parametrize("language,text", [
    ("hi", "मुझे साढ़े दस बजे पानी पीने की याद दिलाना।"),
    ("te", "పదిన్నరకి నీళ్లు తాగమని నాకు గుర్తు చేయండి."),
    ("ta", "பத்து முப்பதுக்கு தண்ணீர் குடிக்க நினைவூட்டுங்கள்."),
    ("bn", "সাড়ে দশটায় আমাকে জল খাওয়ার কথা মনে করিয়ে দাও।"),
    ("as", "সাৰে দহ বজাত মোক পানী খাবলৈ মনত পেলাই দিয়ক।"),
    ("mr", "साडेदहा वाजता मला पाणी पिण्याची आठवण करून द्या."),
    ("kn", "ಹತ್ತೂವರೆ ಗಂಟೆಗೆ ನೀರು ಕುಡಿಯಲು ನನಗೆ ನೆನಪಿಸಿ."),
    ("ml", "പത്തരയ്ക്ക് വെള്ളം കുടിക്കാൻ എന്നെ ഓർമ്മിപ്പിക്കൂ."),
    ("pa", "ਸਾਢੇ ਦਸ ਵਜੇ ਮੈਨੂੰ ਪਾਣੀ ਪੀਣ ਦੀ ਯਾਦ ਦਿਵਾਓ."),
    ("ur", "ساڑھے دس بجے مجھے پانی پینے کی یاد دلائیں۔"),
])
def test_multilingual_hydration_normalizes(language, text):
    result = understand(text, language)
    assert result["language"] == language
    assert result["intent"] == "create_reminder"
    assert result["entities"]["task"] == "drink water"
    assert result["entities"]["time"] == "10:30"
    assert result["entities"]["reminder_type"] == "hydration"
