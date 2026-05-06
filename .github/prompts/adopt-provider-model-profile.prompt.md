I want to add a lightweight provider/model resolution layer to my Python CLI so it supports both:
- profile.model = "google/gemma4"
- CLI override: --model google/gemma4

Constraints:
- Keep the existing requests-based ApiClient architecture.
- Do NOT introduce a large provider framework.
- Do NOT add dependencies.
- Preserve backward compatibility for existing profiles.

Please implement:

1. A new file src/ai_cli/provider_registry.py with:
   - a frozen ProviderSpec dataclass
   - a small alias registry
   - resolve_model_alias(model_name: str | None) -> ProviderSpec | None

2. Support these aliases:
   - google/gemma4 -> gemma-4-26b-a4b-it
   - google/gemma-4-26b-a4b-it -> gemma-4-26b-a4b-it
   - google/gemma-4-31b-it -> gemma-4-31b-it

3. For Google models, the resolver should provide:
   - base_url = https://generativelanguage.googleapis.com
   - endpoint = /v1beta/models/{model_id}:generateContent
   - method = POST
   - auth_header = x-goog-api-key
   - auth_env = GEMINI_API_KEY
   - payload_style = google-generate-content
   - response_text_paths = ("candidates.0.content.parts.0.text",)

4. Update ApiClient:
   - accept model_override: str | None in __init__
   - compute selected_model = model_override or profile.model or profile.name
   - resolve it with resolve_model_alias()
   - if matched, override url/method/payload/auth/response_text_paths
   - keep old behavior for everything else

5. Implement Google payload mapping:
   - input history format is list[dict[str, str]] with role/content
   - map role=user -> role=user
   - map role=assistant -> role=model
   - collect role=system into systemInstruction.parts
   - output payload:
     {
       "contents": [...],
       "systemInstruction": {"parts": [...]}
     }
     only include systemInstruction when needed

6. Improve response extraction:
   - join candidates[0].content.parts[*].text into one string
   - still keep old JSON extraction paths for existing providers
   - if promptFeedback.blockReason exists, return "<blocked: ...>"

7. Show the exact patch for:
   - src/ai_cli/provider_registry.py
   - src/ai_cli/api_client.py
   - any Profile/model field changes
   - sample profile file profiles/google-gemma4.yaml

Please keep the diff minimal and style consistent with the project.