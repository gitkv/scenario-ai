import random
from models.config import DialogueData

def generate_theme(dialogue_data: DialogueData) -> str:
    # Выбираем случайную тему из доступных шаблонов
    theme_template = random.choice(dialogue_data.themes)

    # Выбираем случайных участников диалога
    participants = [character.name for character in dialogue_data.characters]
    num_participants = random.randint(2, 4)  # Нам нужно как минимум два участника
    chosen_participants = random.sample(participants, num_participants)

    # Выбираем случайное настроение, действие, тему и взаимодействие
    chosen_mood = random.choice(dialogue_data.emotions)
    chosen_action = random.choice(dialogue_data.actions)
    chosen_topic = random.choice(dialogue_data.topics)
    chosen_interaction = random.choice(dialogue_data.interactions)

    # Заменяем плейсхолдеры в шаблоне на выбранных участников, настроение, действие и т.д.
    theme = theme_template.format(
        character1=chosen_participants[0],
        character2=chosen_participants[1] if len(chosen_participants) > 1 else chosen_participants[0],
        character3=chosen_participants[2] if len(chosen_participants) > 2 else chosen_participants[0],
        emotion=chosen_mood,
        action=chosen_action,
        topic=chosen_topic,
        interaction=chosen_interaction
    )

    return theme
