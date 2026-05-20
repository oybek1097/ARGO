---
name: Integrate Yandex GPT
slug: yandex-gpt-integration
trigger: yandex gpt, yandexgpt, russian llm, foundation models
category: central-asia
quality: 0.75
author: argo-team
license: MIT
requires_tools: [http_get]
---

# Integrate Yandex GPT

1. Create a Yandex Cloud service account with the `ai.languageModels.user` role.
2. Obtain an IAM token or API key for authentication.
3. Call the Foundation Models completion endpoint with the model URI.
4. Set `temperature` and `maxTokens` per the task.
5. Handle rate limits and keep prompts within the model's context window.
