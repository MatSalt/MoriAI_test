from dataclasses import dataclass
from enum import Enum


class ArtStyle(str, Enum):
    WATERCOLOR = "watercolor"
    VAN_GOGH = "van_gogh"
    FANTASY = "fantasy"
    CARTOON = "cartoon"


STYLE_PROMPTS = {
    ArtStyle.WATERCOLOR: "Fairy tale watercolor style, soft lines and pastel tones, warm and cozy atmosphere, friendly for children, subtle light and shadow",
    ArtStyle.VAN_GOGH: "Vincent van Gogh 'Starry Night' style, swirling brushstrokes and dramatic color contrasts, deep blues and bright yellows, artistic and mystical feeling, softened for fairy tale illustration",
    ArtStyle.FANTASY: "Fantasy illustration style, vivid and bright colors, magical atmosphere, soft texture and light, child-friendly fairy tale illustration",
    ArtStyle.CARTOON: "Cartoon style, clean outlines and bright colors, cute and cheerful atmosphere, simple details, playful fairy tale illustration",
}


@dataclass
class GenerateImagePrompt:
    stories: list[str]
    style_keyword: ArtStyle

    def render(self) -> str:
        diary_text = "\n".join(f"* {entry}" for entry in self.stories)

        return f"""
Create a whimsical, storybook-style illustration in the style of {STYLE_PROMPTS[self.style_keyword]} based on the story: {diary_text}.
Depict the main human characters as they are, and transform all other characters or background figures into animals appropriate for the scene.
Show characters and key elements in dynamic motion, illustrating their actions and interactions with lively expressions and gestures.
Do not include any text, letters, numbers, captions, speech bubbles, or signs in the image.
Use vivid, magical, and charming details to enhance the fairy tale atmosphere.
Focus on composition, lighting, and perspective as if using a low-angle or wide-angle camera to make the scene more immersive.
Optionally, generate the illustration step by step: first background, then main characters, then additional animal characters, and finally magical effects or props.
only one image per story.
"""


# v4 text_input = f"""
# Create a whimsical, storybook-style illustration in the style of {inputData.style} based on the story: {input_data.story}.
# Depict the main human characters as they are, and transform all other characters or background figures into animals appropriate for the scene.
# Show characters and key elements in dynamic motion, illustrating their actions and interactions with lively expressions and gestures.
# Do not include any text, letters, numbers, captions, speech bubbles, or signs in the image.
# Use vivid, magical, and charming details to enhance the fairy tale atmosphere.
# Focus on composition, lighting, and perspective as if using a low-angle or wide-angle camera to make the scene more immersive.
# Optionally, generate the illustration step by step: first background, then main characters, then additional animal characters, and finally magical effects or props.
# """
