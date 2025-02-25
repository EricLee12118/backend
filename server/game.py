from collections import defaultdict
import random
from roles import Wolf, Seer, Witch, Villager

class WerewolfGame:
    def __init__(self):
        self.players = []
        self.events = []
        self.day_count = 1
        self.sheriff = None
        self.sheriff_elect = False
        self.wolf_kill_target = None
        self.human_wolf_votes = defaultdict(int)
    def random_allocate(self):
        num_players = len(self.players)
        roles = []
        werewolf_count = 2 if num_players >= 5 else 1
        roles += [Wolf() for _ in range(werewolf_count)]
        roles += [Seer(), Witch()]
        roles += [Villager() for _ in range(num_players - len(roles))]
        random.shuffle(roles)
        for player, role in zip(self.players, roles):
            player.role = role
    def add_player(self, player):
        self.players.append(player)

    def elect_sheriff(self):
        rounds = 3
        for round_number in range(1, rounds + 1):
            max_votes = max(p.votes for p in self.players if p.alive)
            candidates = [p for p in self.players if p.alive and p.votes == max_votes]
            
            if len(candidates) == 1:
                self.sheriff = candidates[0]
                self.sheriff.sheriff = True
                print(f"\n{self.sheriff.name} 当选警长！")
                self._reset_votes()
                return
            
            print(f"第 {round_number} 轮选举没有选出警长。")
            
            self._reset_votes()
        
        print("警长选举失败，本局没有警长")

    def _reset_votes(self):
        for p in self.players:
            p.votes = 0

    def vote(self):
        alive_players = [p for p in self.players if p.alive]
        max_votes = max(p.votes for p in alive_players)
        candidates = [p for p in alive_players if p.votes == max_votes]
        
        if len(candidates) == 1:
            killed = candidates[0]
            killed.alive = False
            print(f"\n{killed.name} 被投票出局")
            if killed.sheriff:
                self.transfer_sheriff()
        else:
            print("平票，无人出局")
            
        self._reset_votes()

    def transfer_sheriff(self):
        candidates = [p for p in self.players if p.alive and not p.sheriff]
        if candidates:
            new_sheriff = random.choice(candidates)
            self.sheriff = new_sheriff
            new_sheriff.sheriff = True
            print(f"{new_sheriff.name} 成为新警长！")
        else:
            print("没有合适玩家继承警徽")

    def check_game_end(self):
        alive_werewolves = sum(1 for p in self.players if p.is_wolf() and p.alive)
        alive_villagers = sum(1 for p in self.players if not p.is_wolf() and p.alive)
        
        if alive_werewolves == 0:
            print("\n好人阵营胜利！")
            return True
        elif alive_werewolves >= alive_villagers:
            print("\n狼人阵营胜利！")
            return True
        return False

    def day_actions(self):
        print(f"第 {self.day_count} 天白天")
        self.day_count += 1

    def night_actions(self):
        print(f"第 {self.day_count} 天黑夜")
        self.wolf_kill_target = None

        votes = defaultdict(int)
        for player in self.players:
            if player.is_wolf() and player.alive and player.is_ai:  
                action_result = player.night_action(self.players)
                if action_result and "vote" in action_result:
                    target_name = action_result["vote"]
                    votes[target_name] += 1
                    print(f"{player.name} votes for {target_name}")

        for target_name, count in self.human_wolf_votes.items():
            votes[target_name] += count

        print(f"狼人投票结果: {votes}")
        if votes:
            max_votes = max(votes.values())
            candidates = [name for name, count in votes.items() if count == max_votes]
            self.wolf_kill_target = random.choice(candidates) if candidates else None
        
        if self.wolf_kill_target:
            target = next((p for p in self.players if p.name == self.wolf_kill_target), None)
            if target:
                target.alive = False
                print(f"狼人击杀了 {target.name}")
        
        self.human_wolf_votes.clear()