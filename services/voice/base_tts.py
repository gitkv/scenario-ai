from abc import ABC, abstractmethod

class BaseTTS(ABC):
    SUPPORTED_VOICES = []

    def __init__(self):
        if not self.SUPPORTED_VOICES:
            raise NotImplementedError("The SUPPORTED_VOICES list must be populated in the subclass.")
        
    @abstractmethod
    def generate_voice(self, text: str, voice_id: str, output_dir: str, pos: int):
        if not self.is_voice_supported(voice_id):
            raise ValueError(f"The voice '{voice_id}' is not supported. Choose from {self.SUPPORTED_VOICES}.")
        
    def is_voice_supported(self, voice_id):
        return voice_id in self.SUPPORTED_VOICES

    @property
    def supported_voices(self):
        return self.SUPPORTED_VOICES
