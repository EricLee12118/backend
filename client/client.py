import socket
import json

def display_game_status(status):
    print("\n=== 游戏状态 ===")
    print(f"你的角色: {status['role']}")
    print(f"当前天数: {status['day_count']}")
    print("\n玩家状态:")
    for name, role, alive, is_sheriff in status["players"]:
        status_str = "存活" if alive else "已死亡"
        sheriff_str = "(警长)" if is_sheriff else ""
        print(f"{name}: {role} - {status_str} {sheriff_str}")
    print()

class GameClient:
    def __init__(self, host='localhost', port=5000):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((host, port))

    def start(self):
        name = input("请输入你的名字: ")
        self.send_message({"name": name})

        while True:
            message = self.receive_message()
            if not message:
                print("连接断开")
                break

            if not self.handle_message(message):
                break

    def handle_message(self, message):
        message_type = message.get("type")

        if message_type == "wait_confirm":
            print("\n=== 等待游戏确认 ===")
            print("已连接的玩家:", message["players"])
            while True:
                confirm = input("是否准备好开始游戏？(yes/no): ").lower()
                if confirm in ['yes', 'no']:
                    self.send_message({"confirm": confirm == 'yes'})
                    break
                print("无效的输入，请输入 yes 或 no")

        elif message_type == "game_cancelled":
            print("游戏已取消")
            return False

        elif message_type == "game_status":
            display_game_status(message)

        elif message_type == "game_end":
            print("游戏结束")
            return False

        elif message_type == "sheriff_election":
            print("\n=== 警长选举 ===")
            print("可投票的玩家:", message["candidates"])
            while True:
                vote = input("请选择要投票的玩家: ")
                if vote in message["candidates"]:
                    self.send_message({"vote": vote})
                    break
                print("无效的选择，请重新输入")

        elif message_type == "day_vote":
            print("\n=== 白天投票 ===")
            print("可投票的玩家:", message["candidates"])
            while True:
                vote = input("请选择要投票的玩家: ")
                if vote in message["candidates"]:
                    self.send_message({"vote": vote})
                    break
                print("无效的选择，请重新输入")

        elif message_type == "night_action":
            action = message.get("action")
            if action == "werewolf":
                print("\n=== 狼人行动 ===")
                print("可选择的目标:", message["candidates"])
                while True:
                    target = input("请选择要击杀的玩家: ")
                    if target in message["candidates"]:
                        self.send_message({"target": target})
                        break
                    print("无效的选择，请重新输入")

            elif action == "witch":
                print("\n=== 女巫行动 ===")
                if message.get("has_antidote"):
                    print("你可以使用解药拯救一名玩家。")
                    print("死亡的玩家:", message["dead_players"])
                    save = input("请输入要拯救的玩家名字（或输入 'none' 跳过）: ")
                    if save == 'none':
                        save = None
                    elif save not in message["dead_players"]:
                        print("无效的选择，请重新输入")

                if message.get("has_poison"):
                    print("你可以使用毒药毒杀一名玩家。")
                    print("存活的玩家:", message["alive_players"])
                    poison = input("请输入要毒杀的玩家名字（或输入 'none' 跳过）: ")
                    if poison == 'none':
                        poison = None
                    elif poison not in message["alive_players"]:
                        print("无效的选择，请重新输入")

                self.send_message({"save": save, "poison": poison})

            elif action == "seer":
                print("\n=== 预言家行动 ===")
                print("可选择查验的玩家:", message["candidates"])
                while True:
                    target = input("请选择要查验的玩家: ")
                    if target in message["candidates"]:
                        self.send_message({"target": target})
                        break
                    print("无效的选择，请重新输入")

            elif action == "hunter":
                print("\n=== 猎人行动 ===")
                print("可选择的目标:", message["candidates"])
                while True:
                    target = input("请选择要击杀的玩家: ")
                    if target in message["candidates"]:
                        self.send_message({"target": target})
                        break
                    print("无效的选择，请重新输入")

        elif message_type == "seer_result":
            print(f"\n=== 预言家查验结果 ===")
            print(f"玩家 {message['target']} 的身份是: {message['result']}")
        
        return True

    def send_message(self, message):
        try:
            self.client.send(json.dumps(message).encode())
        except:
            print("发送消息失败")

    def receive_message(self):
        try:
            data = self.client.recv(1024)
            return json.loads(data)
        except json.JSONDecodeError:
            print("接收消息失败: JSON解码错误")
            return {}
        except:
            print("接收消息失败")
            return None

if __name__ == "__main__":
    client = GameClient()
    client.start()