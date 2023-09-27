import re

class Translit:
    def __init__(self):
        self.translit_dict = {
            'a': 'а','b': 'б','c': 'к','d': 'д','e': 'е','f': 'ф','g': 'г','h': 'х','i': 'и','j': 'дж','k': 'к','l': 'л','m': 'м','n': 'н','o': 'о','p': 'п','q': 'кв','r': 'р','s': 'с','t': 'т','u': 'у','v': 'в','w': 'в','x': 'кс','y': 'й','z': 'з'
        }
        self.word_translit_dict = {
            'ipad': 'Айпад', 'windows': 'Виндоус', 'line': 'Лайн', 'white': 'Вайт', 'label': 'Лейбл',
            'manager': 'Менеджер', 'jira': 'Джира', 'google': 'Гугл', 'meet': 'Мит', 'telegram': 'Телеграм',
            'overwatch': 'Овервотч', 'design': 'Дизайн', 'linux': 'Линукс', 'bash': 'Баш', 'back-end': 'Бэкенд', 
            'backend': 'Бэкенд', 'it': 'Айти', 'wifi': 'Вайфай', 'youtube': 'Ютуб', 'ios': 'АйОС', 'python': 'Пайтон', 
            'frontend': 'Фронтенд', 'enterprise': 'Энтерпрайз', 'sql': 'ЭсКьюЭль', 'web': 'Веб', 
            'couchdb': 'КаучДБ', 'database': 'Датабейс', 'server': 'Сервер', 'client': 'Клиент', 
            'interface': 'Интерфейс', 'html': 'Хтмл', 'css': 'ЦСС', 'php': 'ПХП', 'java': 'Джава', 
            'c++': 'Си плюс плюс', 'android': 'Андроид', 'api': 'АПИ', 'json': 'Джейсон', 'js': 'ДжиЭс', 'git': 'Гит', 
            'node': 'Нод', 'framework': 'Фреймворк', 'docker': 'Докер', 'kubernetes': 'Кубернетес', 
            'agile': 'Эджайл', 'scrum': 'Скрам', 'kanban': 'Канбан', 'devops': 'ДевОпс', 'algorithm': 'Алгоритм', 
            'data': 'Дэйта', 'query': 'Куэри', 'virtual': 'Виртуал', 'machine': 'Машин', 'network': 'Нетворк', 
            'security': 'Секьюрити', 'firewall': 'Файервол', 'cloud': 'Клауд', 'storage': 'Сторэдж',
            'quick': 'Квик', 'resto': 'Ресто', 'back-office': 'Бэк-офис', 'agile': 'Эджайл', 
            'methodology': 'Методолоджи', 'devops': 'ДевОпс', 'practices': 'Практисес', 'and': 'Энд', 
            'crm': 'ЦэЭрЭм', 'plugin': 'Плагин', 'debug': 'Дебаг', 'code': 'Код', 'script': 'Скрипт',
            'commit': 'Коммит', 'branch': 'Бранч', 'pull': 'Пулл', 'push': 'Пуш', 'app': 'Эпп',
            'laptop': 'Лэптоп', 'desktop': 'Десктоп', 'monitor': 'Монитор', 'mouse': 'Маус',
            'keyboard': 'Кейборд', 'internet': 'Интернет', 'website': 'Вебсайт', 'email': 'Имейл',
            'login': 'Логин', 'password': 'Пассворд', 'account': 'Аккаунт', 'chat': 'Чат', 'overwatch': 'Овервотч',
            'fortnite': 'Фортнайт', 'gta': 'Гэ-Тэ-А', 'minecraft': 'Майнкрафт', 'valorant': 'Валорант', 'apex': 'Апекс',
            'legends': 'Леджендс', 'warzone': 'Варзон', 'cod': 'Кал офф дути', 'pubg': 'Паб-Джи', 'league': 'Лига',
            'rocket': 'Рокет', 'fifa': 'Фифа', 'nba': 'Эн-Би-Эй', 'mmo': 'Эм-Эм-Оу', 'rpg': 'Ар-Пи-Джи',
            'fps': 'ЭфПиЭс', 'rts': 'Ар-Ти-Эс', 'esports': 'Эспортс', 'skin': 'Скин', 'loot': 'Лут', 'box': 'Бокс', 
            'respawn': 'Респаун', 'pvp': 'Пи-Ви-Пи', 'pve': 'Пи-Ви-И', 'raid': 'Рейд', 'quest': 'Квест', 'grind': 'Гринд',
            'level': 'Левел', 'multiplayer': 'Мультиплеер', 'singleplayer': 'Синглплеер', 'coop': 'Кооп', 'dlc': 'Ди-Эл-Си',
            'achievement': 'Ачивмент', '1C': 'о+дин-Эс', 'это': 'э+то', 'эти': 'э+ти', 'э-тих': 'э-ти+х', 'этому': 'э-то+му',
            'ЦРУ': 'Це-Эр+У', 'ФСБ': 'Ф-Эс+Бэ', 'КНР': 'Ка+ЕнЭр', 'КНДР': 'Ка+ЕнДеЭр', 'SpaceX': 'Спэйс+Экс', 'ЛГБТ': 'ЭлГэБэТэ',
            'StarShip': 'Стар+Шип', 'НАТО': 'На+то', 'ООН': 'О+-Он', 'ВТО': 'Вэ-Тэ+О', 'МВФ': 'Эм-Вэ+эф', 'МИД': 'Ми+д',
            'НБА': 'эн-Бе+А', 'ОПЕК': 'О+пек', 'РФ': 'эр-эф', 'США': 'сэ-Шэ-а', 'МММ': 'Эм-Эм+эМ', 'БМВ': 'Бе+эм-Вэ', 'МКС': 'эм-ка-эс',
            'NASA': '+Наса', 'МВД': 'Эм-Вэ+дэ', 
        }
    
    def add_word_mapping(self, word, translit):
        self.word_translit_dict[word.lower()] = translit
    
    def remove_word_mapping(self, word):
        if word.lower() in self.word_translit_dict:
            del self.word_translit_dict[word.lower()]
    
    def replace_words_from_dict(self, text) -> str:
        result = text
        
        for word, translit in self.word_translit_dict.items():
            result = re.sub(r'\b' + re.escape(word) + r'\b', translit, result, flags=re.IGNORECASE)
        
        return result
    
    def transliterate(self, text) -> str:
        result = self.replace_words_from_dict(text)
        
        remaining_words = re.findall(r'\b\w+\b', result)
        for word in remaining_words:
            word_lower = word.lower()
            if word_lower not in self.word_translit_dict:
                translit_word = ''.join([self.translit_dict.get(c.lower(), c) for c in word])
                result = result.replace(word, translit_word)
        
        return result