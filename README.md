# Cogniv AI

## Speech setup

The app uses Azure Speech when both Azure settings are present. Azure's free F0 tier currently includes 5 audio hours per month for speech recognition and 500,000 characters per month for neural speech synthesis. Check Azure's current quotas before deployment.

Create a Speech resource with the **Free F0** tier, then add its key and region to the root `.env` file:

```dotenv
AZURE_SPEECH_KEY=your-resource-key
AZURE_SPEECH_REGION=centralindia
```

The app uses Azure for supported Indian locales and English, and falls back to local speech models for other languages. Without these settings, the current local ASR/TTS engines remain active. For Render, set `AZURE_SPEECH_KEY` as a secret environment variable and keep the region set to the Speech resource's region.

## Multilingual story evidence

To compare spoken answers in all Azure Translator-supported languages against the canonical English story, configure a separate Azure Translator resource in the root `.env` file:

```env
AZURE_TRANSLATOR_KEY=your-translator-resource-key
AZURE_TRANSLATOR_REGION=your-translator-resource-region
AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com
```

`AZURE_TRANSLATOR_KEY` and `AZURE_TRANSLATOR_REGION` are separate from the Speech credentials above. When Translator is not configured or does not support the detected language, the app uses its offline story concepts where available and leaves other answers unscored for caregiver review. When configured, the recognized answer text is sent to Azure Translator for English translation; the original ASR text remains unchanged in the report.

Azure requests send recorded audio for recognition and prompt text for synthesis to Microsoft. Use this option only when that external processing is acceptable for your deployment and patient-data policies.