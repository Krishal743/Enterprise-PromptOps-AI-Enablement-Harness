# Reusable prompt templates

These short templates are for colleagues to **copy and adapt** when prototyping a fictional service workflow. They are separate from the application's versioned `triage_v1.txt` and `triage_v2.txt` prompts. The [manifest](manifest.json) lists each template's purpose, input fields, and review check.

| Template | Use it for | Fill in |
|---|---|---|
| [Structured extraction](structured_extraction.md) | Turn an unstructured note into stated facts | `ticket_text`, `allowed_categories` |
| [Clarifying question](clarifying_question.md) | Ask for details before routing an unclear case | `ticket_text`, `missing_fields` |
| [Customer reply](customer_reply.md) | Draft a response after a supervisor approves the facts | `confirmed_summary`, `approved_guidance`, `tone` |

## Use a template

1. Open the template and copy the text inside its `text` block.
2. Replace each `{parameter}` with a fictional ticket detail or an approved value. Remove the braces after filling it in. For example, in the clarifying-question template, replace `{missing_fields}` with `warning code and when the charging problem began`.
3. Test the filled-in prompt on fictional inputs, including a missing-detail and an instruction-in-the-ticket example. Review the output against the template's **Check** line; do not treat a fluent answer as proof it is correct.
4. For a shared workflow, keep the filled-in prompt in Git, add a golden or red-team case for a failure it fixes, and get a supervisor to review safety-sensitive wording.

Do not paste real customer identifiers or confidential service notes into an unapproved model. The customer-reply template assumes a person has already confirmed the facts and guidance; it does not authorize a repair or dispatch. The application loads its own triage prompts from `prompts/triage_v*.txt`, so editing one of these colleague templates will not change live triage behavior.
