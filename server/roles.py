from abc import ABC, abstractmethod
import random

class Role(ABC):
    def __init__(self, name):
        self.name = name
    @abstractmethod
    def night_action(self, player, all_players):
        pass
    @abstractmethod
    def day_action(self, player, all_players):
        pass

class Wolf(Role):
    def __init__(self):
        super().__init__("狼人")
        
    def night_action(self, player, all_players):
        if player.is_ai:
            valid_targets = [p for p in all_players if p.alive and not p.is_wolf()]
            if valid_targets:
                target = random.choice(valid_targets)
                return {"vote": target.name}
        return None
        
    def day_action(self, player, all_players):
        return None

class Villager(Role):
    def __init__(self):
        super().__init__("平民")
        
    def night_action(self, player, all_players):
        return None
        
    def day_action(self, player, all_players):
        return None

class Witch(Role):
    def __init__(self):
        super().__init__("女巫")
        self.has_poison = True
        self.has_antidote = True
        
    def night_action(self, player, all_players):
        if not player.is_ai:
            return None
            
        if player.is_ai and self.has_antidote:
            dead_players = [p for p in all_players if not p.alive and not p.is_wolf()]
            if dead_players and random.random() < 0.7:  
                target = random.choice(dead_players)
                target.alive = True
                self.has_antidote = False
                return {"action": "save", "target": target.name}
                
        if player.is_ai and self.has_poison:
            valid_targets = [p for p in all_players if p.alive and p.is_wolf()]
            if valid_targets and random.random() < 0.3: 
                target = random.choice(valid_targets)
                target.alive = False
                self.has_poison = False
                return {"action": "poison", "target": target.name}
                
        return None
        
    def day_action(self, player, all_players):
        return None

class Seer(Role):
    def __init__(self):
        super().__init__("预言家")
        
    def night_action(self, player, all_players):
        if not player.is_ai:
            return None
            
        valid_targets = [p for p in all_players if p.alive and p != player]
        if valid_targets:
            target = random.choice(valid_targets)
            result = "狼人" if target.is_wolf() else "好人"
            return {
                "action": "check",
                "target": target.name,
                "result": result
            }
        return None
        
    def day_action(self, player, all_players):
        return None

class Hunter(Role):
    def __init__(self):
        super().__init__("猎人")
        
    def night_action(self, player, all_players):
        return None
        
    def day_action(self, player, all_players):
        if not player.alive:
            if not player.is_ai:
                return None
                
            valid_targets = [p for p in all_players if p.alive and p != player]
            if valid_targets:
                target = random.choice(valid_targets)
                target.alive = False
                return {"target": target.name}
        return None

def create_role(role_name):
    """
    根据角色名创建对应的角色实例
    """
    role_map = {
        "狼人": Wolf,
        "平民": Villager,
        "女巫": Witch,
        "预言家": Seer,
        "猎人": Hunter
    }
    role_class = role_map.get(role_name)
    if role_class:
        return role_class()
    raise ValueError(f"未知角色: {role_name}")