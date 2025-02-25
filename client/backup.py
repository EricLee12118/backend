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
        print("等待两位玩家连接...")
        
        client_socket1, addr1 = self.server.accept()
        print(f"玩家1已连接: {addr1}")
        self.client_sockets.append(client_socket1)
        
        client_socket2, addr2 = self.server.accept()
        print(f"玩家2已连接: {addr2}")
        self.client_sockets.append(client_socket2)
        
        player1_name = self.receive_message(0)["name"]
        player2_name = self.receive_message(1)["name"]
    
        player1 = Player(player1_name)
        player2 = Player(player2_name)
        self.players = [player1, player2]
        
        self.broadcast_message({"type": "wait_confirm", "players": [player1_name, player2_name]})
        
        confirm1 = self.receive_message(0)["confirm"]
        confirm2 = self.receive_message(1)["confirm"]
        
        if confirm1 and confirm2:
            self.game.add_player(player1)
            self.game.add_player(player2)
            
            for i in range(6):  
                self.game.add_player(Player(f"AI玩家{i+1}"))
                
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

        valid_candidates = [p for p in self.game.players if p.alive and p not in self.players]
        for voter in valid_candidates:
            with self.vote_lock:
                target = random.choice(valid_candidates)
                target.votes += 1
                print(f"{voter.name, voter.role.name} 投票给 {target.name}")

        for thread in vote_threads:
            thread.join()

        self.game.vote()

    def player_day_vote(self, player_index, player):
        data = {
            "type": "day_vote",
            "candidates": [p.name for p in self.game.players if p.alive and p != player]
        }
        self.send_message(data, player_index)
        
        response = self.receive_message(player_index)
        target_name = response["vote"]
        
        with self.vote_lock:
            target = next((p for p in self.game.players if p.name == target_name), None)
            if target:
                target.votes += 1.5 if player.sheriff else 1

    def handle_night_phase(self):
        action_threads = []

        for i, player in enumerate(self.players):
            if player.alive and player.is_wolf():
                thread = threading.Thread(
                    target=self.player_night_action,
                    args=(i, player)
                )
                action_threads.append(thread)
                thread.start()

        for thread in action_threads:
            thread.join()

        self.game.night_actions()

    def player_night_action(self, player_index, player):
        self.send_message({
            "type": "night_action",
            "action": "werewolf",
            "candidates": [p.name for p in self.game.players if p.alive and not p.is_wolf()]
        }, player_index)
        
        response = self.receive_message(player_index)
        target_name = response["target"]
        
        with self.vote_lock:
            target = next((p for p in self.game.players if p.name == target_name), None)
            if target:
                target.alive = False
    
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