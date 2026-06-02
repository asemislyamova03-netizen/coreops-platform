import re

PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def extract_placeholders(template_body: str) -> set[str]:
    return set(PLACEHOLDER_PATTERN.findall(template_body))


def render_template(template_body: str, context: dict[str, str]) -> str:
    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            raise KeyError(key)
        return str(context[key])

    return PLACEHOLDER_PATTERN.sub(replacer, template_body)
