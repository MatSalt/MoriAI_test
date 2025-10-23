from dataclasses import dataclass


@dataclass
class GenerateVideoPrompt:
    stories: list[str]

    def render(self) -> str:
        diary_text = "\n".join(f"* {entry}" for entry in self.stories)

        return f"""{diary_text}.
        *Make it the same as the provided image ratio.*"""
