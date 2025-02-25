# server/events.py
from abc import ABC, abstractmethod

class GameEvent(ABC):
    def __init__(self, name, description):
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, game):
        pass

class DayEvent(GameEvent):
    def __init__(self, name, description):
        super().__init__(name, description)
    def execute(self, game):
        if not game.sheriff:
            print("警长选举", "玩家投票选举警长")
            game.elect_sheriff()
        print(f"\n=== {self.name} ===")
        game.day_actions()
        game.vote()

class NightEvent(GameEvent):
    def __init__(self, name, description):
        super().__init__(name, description)
        
    def execute(self, game):
        print(f"\n=== {self.name} ===")
        game.night_actions()