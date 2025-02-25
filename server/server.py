import random
import socket
import json
import threading
import time
from game import WerewolfGame
from models import Player
from events import DayEvent, NightEvent

class GameServer:
    def __init__(self, host='localhost', port=5000):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(2)  
        self.game = WerewolfGame()
        self.players = []
        self.client_sockets = []
        self.vote_lock = threading.Lock()


    def start(self):
        print("等待玩家连接...")

        num_real_players = 8  
        num_ai_players = 0    

        self.client_sockets = []
        for i in range(num_real_players):
            client_socket, addr = self.server.accept()
            print(f"玩家{i + 1}已连接: {addr}")
            self.client_sockets.append(client_socket)

        self.players = []
        for i in range(num_real_players):
            player_name = self.receive_message(i)["name"]
            self.players.append(Player(player_name))

        self.broadcast_message({"type": "wait_confirm", "players": [player.name for player in self.players]})

        confirmations = [self.receive_message(i)["confirm"] for i in range(num_real_players)]

        if all(confirmations):
            for player in self.players:
                self.game.add_player(player)

            names = ['Stephanie', 'Wendy', 'Elmy', 'Sham', 'Jeffry', 'Kelly']  
            for i in range(num_ai_players):
                if i < len(names):  
                    self.game.add_player(Player(names[i], is_ai=True))

            self.game.random_allocate()
            self.send_game_status()

            self.game.events = [
                NightEvent("黑夜", "狼人行动"),
                DayEvent("白天", "讨论和投票"),
            ]

            self.run_game()
        else:
            self.broadcast_message({"type": "game_cancelled"})

    def broadcast_message(self, message):
        for sc in self.client_sockets:
            try:
                sc.send(json.dumps(message).encode())
            except:
                print("发送消息失败")
                
    def send_game_status(self):
        for i, player in enumerate(self.players):
            status = {
                "type": "game_status",
                "role": player.role.name,
                "players": [(p.name, p.role.name if p == player or p.is_wolf() and player.is_wolf() else "未知", 
                            p.alive, p.sheriff) for p in self.game.players],
                "day_count": self.game.day_count
            }
            self.send_message(status, i)
            
    def run_game(self):
        print("=== 狼人杀游戏开始 ===")

        while True:
            for event in self.game.events:
                if isinstance(event, NightEvent):
                    self.handle_night_phase()
                if not self.game.sheriff and not self.game.sheriff_elect:
                    self.handle_sheriff_election()
                    self.game.sheriff_elect = True
                if not self.game.sheriff and self.game.sheriff_elect:
                    self.game.transfer_sheriff()
                elif isinstance(event, DayEvent):
                    self.handle_day_phase()
                
                time.sleep(1)
                self.send_game_status()
                    
                if self.game.check_game_end():
                    self.broadcast_message({"type": "game_end"})
                    return

    def handle_sheriff_election(self):
        vote_threads = []

        for i, player in enumerate(self.players):
            if player.alive:
                thread = threading.Thread(
                    target=self.player_sheriff_vote,
                    args=(i, player)
                )
                vote_threads.append(thread)
                thread.start()

        valid_candidates = [p for p in self.game.players if p.alive and p not in self.players]
        for voter in valid_candidates:
            with self.vote_lock:
                target = random.choice(valid_candidates)
                target.votes += 1
                print(f"{voter.name, voter.role.name} 投票给 {target.name}")

        for thread in vote_threads:
            thread.join()

        self.game.elect_sheriff()

    def player_sheriff_vote(self, player_index, player):
        self.send_message({
            "type": "sheriff_election",
            "candidates": [p.name for p in self.game.players if p.alive]
        }, player_index)
        
        response = self.receive_message(player_index)
        target_name = response["vote"]
        
        with self.vote_lock:
            target = next((p for p in self.game.players if p.name == target_name), None)
            if target:
                target.votes += 1
    def player_day_vote(self, player_index, player):
        data = {
            "type": "day_vote",
            "candidates": [p.name for p in self.game.players if p.alive and p != player]
        }
        self.send_message(data, player_index)
        
        response = self.receive_message(player_index)
        if response and "vote" in response:
            target_name = response["vote"]
            
            with self.vote_lock:
                target = next((p for p in self.game.players if p.name == target_name), None)
                if target:
                    target.votes += 1.5 if player.sheriff else 1
                    print(f"{player.name} ({player.role.name}) 投票给 {target.name}")
    def handle_night_phase(self):
        night_lock = threading.Lock()
        # 阶段1: 狼人行动（所有狼人优先行动）
        def process_wolves():
            wolf_threads = []
            for i, player in enumerate(self.game.players):
                if player.alive and player.is_wolf() and not player.is_ai:
                    thread = threading.Thread(
                        target=self.player_night_action,
                        args=(i, player, "werewolf")
                    )
                    wolf_threads.append(thread)
                    thread.start()
            for thread in wolf_threads:
                thread.join()

        # 阶段2: 女巫行动（狼人行动完成后执行）
        def process_witches():
            witch_threads = []
            for player in self.game.players:
                if player.alive and player.is_witch() and player.is_ai:
                    action_result = player.night_action(self.game.players)
                    if action_result:
                        with night_lock:
                            print(f"女巫 {player.name} (AI) 执行行动: {action_result}")
            for i, player in enumerate(self.game.players):
                if player.alive and player.is_witch() and not player.is_ai:
                    thread = threading.Thread(
                        target=self.player_night_action,
                        args=(i, player, "witch")
                    )
                    witch_threads.append(thread)
                    thread.start()
            for thread in witch_threads:
                thread.join()

        # 阶段3: 预言家行动（女巫行动完成后执行）
        def process_seers():
            seer_threads = []
            for player in self.game.players:
                if player.alive and player.is_seer() and player.is_ai:
                    action_result = player.night_action(self.game.players)
                    if action_result:
                        with night_lock:
                            print(f"预言家 {player.name} (AI) 执行行动: {action_result}")
            for i, player in enumerate(self.game.players):
                if player.alive and player.is_seer() and not player.is_ai:
                    thread = threading.Thread(
                        target=self.player_night_action,
                        args=(i, player, "seer")
                    )
                    seer_threads.append(thread)
                    thread.start()
            for thread in seer_threads:
                thread.join()

        def process_hunters():
            hunter_threads = []
            for player in self.game.players:
                if not player.alive and player.is_hunter() and player.is_ai:
                    action_result = player.night_action(self.game.players)
                    if action_result:
                        with night_lock:
                            print(f"猎人 {player.name} (AI) 执行行动: {action_result}")
            for i, player in enumerate(self.game.players):
                if not player.alive and player.is_hunter() and not player.is_ai:
                    thread = threading.Thread(
                        target=self.player_night_action,
                        args=(i, player, "hunter")
                    )
                    hunter_threads.append(thread)
                    thread.start()
            for thread in hunter_threads:
                thread.join()

        process_wolves()      
        process_witches()     
        process_seers()       
        # process_hunters()     

        self.game.night_actions()

    def handle_day_phase(self):
        self.game.day_actions()

        vote_threads = []

        for i, player in enumerate(self.players):
            if player.alive:
                thread = threading.Thread(
                    target=self.player_day_vote,
                    args=(i, player)
                )
                vote_threads.append(thread)
                thread.start()

        valid_candidates = [p for p in self.game.players if p.alive]
        for voter in valid_candidates:
            if voter.is_ai:  
                vote_candidates = [p for p in self.game.players if p.alive and p != voter]
                with self.vote_lock:
                    if vote_candidates:
                        target = random.choice(vote_candidates)
                        target.votes += 1
                        print(f"{voter.name} ({voter.role.name}) 投票给 {target.name}")
                    else:
                        print(f"{voter.name} 没有可投票的目标")

        for thread in vote_threads:
            thread.join()

        self.game.vote()

    def player_night_action(self, player_index, player, role_type):
        try:
            if role_type == "werewolf":
                candidates = [p.name for p in self.game.players if p.alive and not p.is_wolf()]
                self.send_message({
                    "type": "night_action",
                    "action": "werewolf",
                    "candidates": candidates
                }, player_index)
                
                response = self.receive_message(player_index)
                if response and "target" in response:
                    with self.vote_lock:
                        target_name = response["target"]
                        self.game.human_wolf_votes[target_name] += 1
                        print(f"狼人 {player.name} (真人) 选择击杀 {target_name}")

            elif role_type == "witch":
                dead_players = [p.name for p in self.game.players if not p.alive]
                alive_players = [p.name for p in self.game.players if p.alive and p != player]
                self.send_message({
                    "type": "night_action",
                    "action": "witch",
                    "has_poison": player.role.has_poison,
                    "has_antidote": player.role.has_antidote,
                    "dead_players": dead_players,
                    "alive_players": alive_players
                }, player_index)
                
                response = self.receive_message(player_index)
                if response:
                    if "save" in response and player.role.has_antidote:
                        target_name = response["save"]
                        target = next((p for p in self.game.players if p.name == target_name), None)
                        if target and not target.alive:
                            target.alive = True
                            player.role.has_antidote = False
                            print(f"女巫 {player.name} (真人) 使用解药救活 {target_name}")
                    if "poison" in response and player.role.has_poison:
                        target_name = response["poison"]
                        target = next((p for p in self.game.players if p.name == target_name), None)
                        if target and target.alive:
                            target.alive = False
                            player.role.has_poison = False
                            print(f"女巫 {player.name} (真人) 使用毒药击杀 {target_name}")
            elif role_type == "seer":
                candidates = [p.name for p in self.game.players if p.alive and p != player]
                self.send_message({
                    "type": "night_action",
                    "action": "seer",
                    "candidates": candidates
                }, player_index)
                
                response = self.receive_message(player_index)
                if response and "target" in response:
                    target_name = response["target"]
                    target = next((p for p in self.game.players if p.name == target_name), None)
                    if target:
                        role = "狼人" if target.is_wolf() else "好人"
                        self.send_message({
                        "type": "seer_result",
                        "action": "seer",
                        "target": target_name,
                        "result": role,
                        }, player_index)

            elif role_type == "hunter":
                candidates = [p.name for p in self.game.players if p.alive and p != player]
                self.send_message({
                    "type": "night_action",
                    "action": "hunter",
                    "candidates": candidates
                }, player_index)
                
                response = self.receive_message(player_index)
                if response and "target" in response:
                    target_name = response["target"]
                    target = next((p for p in self.game.players if p.name == target_name), None)
                    if target:
                        target.alive = False
                        print(f"猎人 {player.name} (真人) 带走了 {target_name}")
        except Exception as e:
            print(f"处理玩家 {player.name} 夜间行动时发生错误: {str(e)}")
        
    def send_message(self, message, player_index):
        try:
            self.client_sockets[player_index].send(json.dumps(message).encode())
        except:
            print("发送消息失败")
        
    def receive_message(self, player_index):
        try:
            return json.loads(self.client_sockets[player_index].recv(1024).decode())
        except json.JSONDecodeError:
            print("接收消息失败: JSON解码错误")
            return {}
        except Exception as e:
            print(f"接收消息失败: {e}")
            return {}
        
if __name__ == "__main__":
    server = GameServer()
    server.start()

