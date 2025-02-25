from roles import Wolf, Villager, Seer, Witch

class Player:
    def __init__(self, name, is_ai=False):
        self.name = name
        self.role = None
        self.is_ai = is_ai
        self.alive = True
        self.votes = 0
        self.sheriff = False

    def night_action(self, all_players):
        if self.role:
            return self.role.night_action(self, all_players)
        return None

    def day_action(self, all_players):
        if self.role:
            return self.role.day_action(self, all_players)
        return None
    
    def is_wolf(self):
        return isinstance(self.role, Wolf)
    
    def is_seer(self):
        return isinstance(self.role, Seer)
    
    def is_witch(self):
        return isinstance(self.role, Witch)
    
    def is_villager(self):
        return isinstance(self.role, Villager)