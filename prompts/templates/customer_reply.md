# Customer reply

**Use when:** a supervisor has already confirmed the route and approved guidance.

**Parameters:** `{confirmed_summary}`, `{approved_guidance}`, `{tone}`.

```text
Draft a concise {tone} reply. Use only these confirmed facts: {confirmed_summary}.
Use only this approved guidance: {approved_guidance}. Do not promise a repair,
price, appointment, or response time. If guidance is missing, request human review.
```

**Check:** the reply contains no diagnosis or promise beyond the supplied facts.
