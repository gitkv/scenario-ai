import pymorphy2
from typing import List

class TextFilter:
    def __init__(self, banned_words_list: List[str]):
        self.morph = pymorphy2.MorphAnalyzer()
        self.banned_words = set([self.morph.parse(word.strip())[0].normal_form for word in banned_words_list])
    
    def is_forbidden(self, text: str) -> bool:
        words = text.split()
        for word in words:
            lemma = self.morph.parse(word)[0].normal_form
            if lemma in self.banned_words:
                return True
        return False
