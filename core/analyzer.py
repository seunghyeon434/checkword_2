from core.ai_client import AIClient


class TextAnalyzer:
    def __init__(self):
        self.ai = AIClient()

    def analyze_spelling(self, text):
        result = self.check_spelling(text)
        return self.format_spell_check(result)

    def analyze_summary(self, text):
        result = self.summarize(text)
        return self.format_summary(result)

    def analyze_evaluation(self, text):
        return "100점"

    def analyze_title_recommendation(self, text):
        return "Writing Assistant"

    def analyze_tone_change(self, text, tone):
        return text

    def check_spelling(self, text):
        prompt = f"맞춤법 검사\n{text}"
        return self.ai.request(prompt)

    def summarize(self, text):
        prompt = f"요약\n{text}"
        return self.ai.request(prompt)

    def format_spell_check(self, result):
        issues = ""
        corrected = ""

        if isinstance(result, dict):
            issues = result.get("issues", "")
            corrected = result.get("corrected", "")
        else:
            corrected = str(result)

        sections = ["맞춤법 검사 결과:"]
        if issues.strip():
            sections.extend(["", issues.strip()])

        sections.extend(["", "맞춤법 수정 결과:", "", corrected.strip()])
        return "\n".join(sections).rstrip()

    def format_summary(self, result):
        summary_text = str(result).strip()
        return f"요약 결과:\n\n{summary_text}"
