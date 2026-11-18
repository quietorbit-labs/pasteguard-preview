# PasteGuard

Hide recognized secrets before sharing debugging text.

## Try the current preview

[**Open the free browser demo**](https://pasteguard.pages.dev/?utm_source=github&utm_medium=readme&utm_campaign=first_tester#demo). Click **Try a fake example** to see detected values replaced with `[REDACTED]`. No account is required.

If you paste logs or configs into AI chats, [tell us whether this helps your workflow](https://github.com/quietorbit-labs/pasteguard-preview/issues/1). One sentence about what worked or blocked you helps improve the preview.

[Install the current v0.6.1 Chrome preview](https://pasteguard.pages.dev/install-guide). Download the ZIP from that guide, then use Chrome's **Load unpacked** setup. The guide also has an optional installation check.

The demo scans text locally. Website visits are measured in aggregate. PasteGuard can miss secrets, and support varies by editor. Test with fake data and review before sharing.

## Repository source and optional local AI

The source below documents the earlier v0.3.0 local AI build. For the current downloadable browser preview, use the installation guide above.

**This is a test build, not complete leak protection.** Rules detect selected API keys and labeled credentials. Optional local AI adds context-based names, locations and selected private identifiers after a 300 ms typing pause. Optional guessing handles some unlabeled mixed-character passwords. All switches start OFF.

AI can miss secrets or redact harmless text. It does not protect every app, understand all confidential information, or guarantee under 10 ms. Text already typed can reach a destination before detection. No company service or payments are available.

## Download and install

[Download the current source ZIP](https://github.com/quietorbit-labs/pasteguard-preview/archive/refs/heads/main.zip). Extract it. Open chrome://extensions in Chrome, enable Developer mode, choose Load unpacked and select the **extension** folder. Disable your old PasteGuard install to avoid two copies changing text. Reload supported AI tabs after updating.

The extension runs on ChatGPT, Claude and Gemini in Chrome. **Live editor compatibility is still unverified.** Plain text fields are the intended test surface. Do not use real secrets until you have validated behavior; no detection result guarantees safety.

## Start local AI

Requires Python 3.11 or later on the computer. From the extracted project folder, run:

```powershell
python -m pip install -r local-ai/requirements.txt
python local-ai/setup.py
python local-ai/server.py
```

Setup downloads about 29 MB of model weights and tokenizer files from Hugging Face. Pip downloads dependencies from PyPI. Then inference works without cloud AI. Leave the server running; Ctrl+C stops it. It listens only on 127.0.0.1:4322. No Windows keyboard hooks or startup service are installed. The local test page is http://127.0.0.1:4322/.

Open the extension popup. Turn ON **Auto-redaction on AI websites**, then **Local AI context detection**. Optional **Detect likely unlabeled secrets** can flag harmless text. If the AI program is stopped, AI reports unavailable and the rules remain active. Manual checker in the popup uses rules only.

The extension now requests permission for http://127.0.0.1/* so its worker can reach the local program. The worker's code only contacts fixed endpoint http://127.0.0.1:4322/scan; it does not accept arbitrary destination URLs. Text is sent from the extension to that local process only when both auto-redaction and local AI are ON. It is processed in memory; no snippet logs or telemetry. This localhost permission is additional to the older pattern-only release.

## What was checked

- 32 detector/package checks on selected patterns and guessing mode.
- Local AI audited on 10 fake examples; results and misses in local-ai/AUDIT.json. This is not an accuracy estimate.
- Browser typing on the local test page: name/location redaction ON, unchanged text OFF, mixed credentials/email with combined detection.
- Basic local API checks: size limits, foreign-origin and missing-header rejection.
- Extension integration is tested using a synthetic browser fixture with mocked Chrome messaging. A real installed Chrome/AI-editor test is still required before making protection claims.

The AI supports at most 2,000 characters / 512 tokens per scan. Oversize input reports an error instead of silently partially scanning. AI stale results are discarded after edits, focus changes or turning OFF. Turning OFF does not restore text already redacted.

## Interest and feedback

[Report a fake-data test result](https://github.com/quietorbit-labs/pasteguard-preview/issues/new?template=free-preview-feedback.yml). [Public team-interest form](https://github.com/quietorbit-labs/pasteguard-preview/issues/new?template=team-waitlist.yml). Proposed $500/month team features are not implemented. Interest is not a purchase. Do not include private information in public GitHub issues. Sharing is voluntary.

## Model

Model and card: https://huggingface.co/onnx-community/bert-small-pii-detection-ONNX (Apache 2.0 according to the card). Revision: 6cb4e77c2b2c7f81e731b88cffa9b7a6fc675a4c. Setup verifies the ONNX weight hash. No remote model Python code is executed. The AI model can miss unlabeled passwords and API keys; rules remain important.

