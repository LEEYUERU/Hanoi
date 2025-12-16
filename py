import time
import sys
import json
import os
import textwrap
import re
import random
from colorama import init, Fore, Style

# --- 顏色與 UI 主題設定 ---
colors = {"system": Fore.YELLOW, "girl": Fore.MAGENTA, "friend": Fore.CYAN, "stat_up": Fore.GREEN, "stat_down": Fore.RED, "scene": Fore.WHITE, "locked": Style.DIM + Fore.WHITE, "error": Fore.RED + Style.BRIGHT, "prompt": Fore.WHITE, "stat_name": Style.BRIGHT, "inventory": Fore.BLUE, "time": Fore.LIGHTBLUE_EX, "border": Style.DIM, "title": Fore.YELLOW + Style.BRIGHT, "stamina": Fore.GREEN}
BOX_CHARS = {"tl": "╔", "tr": "╗", "bl": "╚", "br": "╝", "h": "═", "v": "║", "ts": "╤", "bs": "╧", "ls": "╟", "rs": "╢", "cs": "╫"}

# --- 全域設定 ---
SAVE_FILE = "savegame.json"
PERIODS = ["上午", "下午", "晚上"]
STAMINA_RECOVERY_ON_SLEEP = 40 # 晚上睡覺恢復的體力 (已降低)

# --- 輔助函式：計算文字顯示寬度 (中文字算2格) ---
def get_str_width(s):
    return sum(2 if ord(c) > 255 else 1 for c in s)

# --- UI 繪製函式 ---
def draw_box(title, content_lines, width):
    title_width = get_str_width(title)
    print(colors["border"] + BOX_CHARS["tl"] + BOX_CHARS["h"] * 2 + f" {colors['title']}{title}{colors['border']} " + BOX_CHARS["h"] * (width - title_width - 5) + BOX_CHARS["tr"] + Style.RESET_ALL)
    for line in content_lines:
        clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
        visible_len = get_str_width(clean_line)
        padding = width - visible_len - 2
        padding = max(0, padding) # 確保不會是負數
        print(colors["border"] + BOX_CHARS["v"] + Style.RESET_ALL + f" {line}{' ' * padding}" + colors["border"] + BOX_CHARS["v"] + Style.RESET_ALL)
    print(colors["border"] + BOX_CHARS["bl"] + BOX_CHARS["h"] * (width - 2) + BOX_CHARS["br"] + Style.RESET_ALL)

def prepare_state_lines(player, npcs):
    lines = []
    stamina_color = colors['stamina'] if player['stamina'] > 30 else colors['error']
    lines.append(f"💪 {colors['stat_name']}體力:{Style.RESET_ALL} {stamina_color}{player['stamina']:<4}{Style.RESET_ALL} | 💰 {colors['stat_name']}財富:{Style.RESET_ALL} {player['wealth']:<4} | 🎓 {colors['stat_name']}智慧:{Style.RESET_ALL} {player['intelligence']:<4}")
    lines.append(f"✨ {colors['stat_name']}顏值:{Style.RESET_ALL} {player['appearance']:<4} | 📏 {colors['stat_name']}身高:{Style.RESET_ALL} {player['height']:<4}cm")
    inventory_text = ', '.join(player['inventory']) if player['inventory'] else '空'
    lines.append(f"🎒 {colors['stat_name']}背包:{Style.RESET_ALL} {colors['inventory']}{inventory_text}{Style.RESET_ALL}")
    lines.append(BOX_CHARS["ls"] + BOX_CHARS["h"]*3 + f" {Style.BRIGHT}人物關係{Style.NORMAL} " + BOX_CHARS["h"]*3 + BOX_CHARS["rs"])
    lines.append(f"❤️  {colors['girl']}文靜的她 (好感度): {npcs['girl']['affection']}{Style.RESET_ALL}")
    lines.append(f"🧡  {colors['friend']}青梅竹馬 (好感度): {npcs['friend']['affection']}{Style.RESET_ALL}")
    return lines

# --- 存檔/讀檔功能 ---
def save_game(player, npcs, time, scene_id):
    save_data = {"player_stats": player, "npc_stats": npcs, "time_stats": time, "current_scene_id": scene_id}
    try:
        with open(SAVE_FILE, 'w', encoding='utf-8') as f: json.dump(save_data, f, ensure_ascii=False, indent=4)
    except Exception: pass
def load_game():
    if not os.path.exists(SAVE_FILE): return None, None, None, None
    try:
        with open(SAVE_FILE, 'r', encoding='utf-8') as f: save_data = json.load(f)
        return save_data["player_stats"], save_data["npc_stats"], save_data["time_stats"], save_data["current_scene_id"]
    except Exception: return None, None, None, None

# --- 遊戲資料 ---
player_stats = {"wealth": 2500, "intelligence": 5, "appearance": 5, "height": 165, "inventory": [], "stamina": 100, "flags": []}
npc_stats = {"girl": {"affection": 0, "trust": 0}, "friend": {"affection": 20, "jealousy": 0}}
time_stats = {"day": 1, "period_index": 0}
scheduled_events = {"7": "exam_announcement", "8": "exam_scene"}

story = {
    "daily_router": {"type": "router", "routes": [
        {"scene": "morning_text_from_girl", "conditions": {"npcs": {"girl": {"min_affection": 20}}}},
        {"scene": "morning_text_from_friend", "conditions": {"npcs": {"friend": {"min_affection": 30}}}},
        {"scene": "event_lucky_money", "conditions": {"random_chance": 0.1}},
        {"scene": "event_bad_weather", "conditions": {"random_chance": 0.1}},
        {"scene": "event_cat_encounter", "conditions": {"random_chance": 0.15}},
        {"scene": "morning_random_rain", "conditions": {"random_chance": 0.2}},
        {"scene": "start", "conditions": {}}
    ]}, # 預設場景
    "morning_text_from_girl": {"text": "手機亮了一下，是她傳來的早安訊息，簡單的問候讓你開心了一整天。", "choices": [{"text": "1. 開始美好的一天。", "next_scene": "start"}]},
    "morning_text_from_friend": {"text": "你的青梅竹馬傳來一個有趣的梗圖，你笑著開始了新的一天。", "choices": [{"text": "1. 開始新的一天。", "next_scene": "start"}]},
    "morning_random_rain": {"text": "窗外下起了濛濛細雨，天氣涼爽，適合待在室內。", "choices": [{"text": "1. 開始下雨的一天。", "next_scene": "start"}]},
    "event_lucky_money": {"text": "你在上學的路上意外撿到了 50 元！運氣真不錯。", "effects": {"player": {"wealth": 50}}, "choices": [{"text": "1. 收進口袋，開始新的一天。", "next_scene": "start"}]},
    "event_bad_weather": {"text": "突然下起傾盆大雨，你沒帶傘，被淋成了落湯雞...感覺體力流失了。", "effects": {"player": {"stamina": -10}}, "choices": [{"text": "1. 趕緊跑去學校。", "next_scene": "start"}]},
        "event_cat_encounter": {"text": "你在路邊遇到一隻親人的流浪貓，跟牠玩了一會兒，心情變好了。", "effects": {"player": {"stamina": 5}}, "choices": [{"text": "1. 真是可愛。", "next_scene": "start"}]},
        "start": {"text": "一個新的早晨，陽光透過窗戶灑進房間。今天你想做些什麼呢？", "choices": [{"text": "1. 去圖書館念書。", "next_scene": "library_intro"}, {"text": "2. 找青梅竹馬出去玩。", "next_scene": "hangout_with_friend", "effects": {"npcs": {"friend": {"affection": 5}}, "player": {"stamina": -30}}}, {"text": "3. 待在家裡小睡一下，恢復體力。", "next_scene": "rest_at_home", "effects": {"player": {"stamina": 40}}}, {"text": "4. 去健身房鍛鍊 (提升顏值)。", "next_scene": "gym_workout", "effects": {"player": {"appearance": 1, "stamina": -35}}}, {"text": "5. 去便利商店打工。", "next_scene": "work_conveniencestore", "effects": {"player": {"wealth": 200, "stamina": -40}}}]},
        "go_home_alone": {"text": "這個時段結束了，你準備迎接下一個時段的到來。", "choices": [{"text": "1. 繼續...", "next_scene": "daily_router"}]}, # 指向路由
        "library_intro": {"text": "你來到圖書館，不遠處那位安靜的女孩也在。你注意到她似乎在為一道難題苦惱。", "choices": [{"text": "1. 上前耐心指導她。", "next_scene": "help_her_study", "effects": {"npcs": {"girl": {"affection": 10, "trust": 5}}, "player": {"intelligence": 2, "stamina": -20}}, "requirements": {"min_stats": {"stamina": 40, "intelligence": 10}}}, {"text": "2. (好累...不想動) 找個角落自己念書。", "next_scene": "study_alone_tired", "effects": {"player": {"stamina": -10}}, "requirements": {"max_stats": {"stamina": 39}}}, {"text": "3. 專心念自己的書。", "next_scene": "study_hard", "effects": {"player": {"intelligence": 10, "stamina": -25}}}]},
        "study_hard": {"text": "你專心於學業，感覺自己的智慧提升了。", "choices": [{"text": "1. 結束這個時段。", "next_scene": "go_home_alone"}]},
         "study_alone_tired": {"text": "你太累了，實在沒精力去社交。你找了個角落坐下，勉強看了幾頁書，但什麼都沒看進去。", "choices": [{"text": "1. 結束這個時段。", "next_scene": "go_home_alone"}]},
         "hangout_with_friend": {"text": "你和青梅竹馬在球場上揮灑汗水，度過了一個愉快的下午。", "choices": [{"text": "1. 結束今天吧。", "next_scene": "go_home_alone"}]},
         "rest_at_home": {"text": "你拉上窗簾，在床上小睡了一會兒，感覺精神好多了。", "choices": [{"text": "1. 結束這個時段。", "next_scene": "go_home_alone"}]},
        "work_conveniencestore": {"text": "你在便利商店辛苦地工作，雖然很累，但薪水讓你的口袋充實了不少。", "choices": [{"text": "1. 結束這個時段。", "next_scene": "go_home_alone"}]},
        "gym_workout": {"text": "你在健身房努力鍛鍊，汗水浸濕了衣服，但感覺身材更好了。", "choices": [{"text": "1. 結束這個時段。", "next_scene": "go_home_alone"}]},
        "help_her_study": {"text": "在你的幫助下，她很快解開了難題，並對你露出了感激的微笑。「你真厲害！」", "choices": [{"text": "1. 邀請她週末去看電影。", "next_scene": "ask_for_date", "effects": {"add_flags": ["date_agreed"]}, "requirements": {"npcs": {"girl": {"min_affection": 5}}, "min_stats": {"stamina": 20, "appearance": 8, "intelligence": 8}}}, {"text": "2. (疲憊地)「沒什麼。」", "next_scene": "go_home_alone", "effects": {"npcs": {"girl": {"affection": -2}}}, "requirements": {"max_stats": {"stamina": 19}}}, {"text": "3. 禮貌告別。", "next_scene": "go_home_alone"}]},
        "ask_for_date": {"text": "她答應了你的邀約！你們約好週末在電影院見面。你忍不住和青梅竹馬分享了這件事。", "effects": {"npcs": {"friend": {"jealousy": 10}}}, "choices": [{"text": "1. 期待週末的到來。", "next_scene": "go_home_alone"}]},    "exam_announcement": {"text": "【公告】\n\"提醒各位同學，期末考試將在明天舉行，請做好準備。\"", "choices": [{"text": "1. (今晚必須通宵複習了...)", "next_scene": "study_hard", "effects": {"player": {"intelligence": 15, "stamina": -40}}}]},
    "exam_scene": {"type": "event_trigger", "event_type": "exam", "pass_threshold": 50, "pass_scene": "exam_pass", "fail_scene": "exam_fail"},
    "exam_pass": {"text": "考試結果公佈，你的成績非常優異！這段時間的努力沒有白費。", "effects": {"player": {"intelligence": 10}}, "choices": [{"text": "1. 太好了！", "next_scene": "daily_router"}]},
    "exam_fail": {"text": "你看著不及格的成績單，心中充滿了悔恨。", "effects": {"player": {"intelligence": -10}}, "choices": [{"text": "1. 唉...", "next_scene": "daily_router"}]},
    "final_ending": {"type": "final_eval"}, "ending_perfect": {"text": "結局：完美人生..."}, "ending_love_lost_friend": {"text": "結局：遺失的友情..."}, "ending_scholar": {"text": "結局：孤高的學者..."},
}

# --- 角色創建 ---
def character_creation():
    stats = {"wealth": 2500, "intelligence": 5, "appearance": 5, "height": 165}
    points = 20
    stat_names = {"1": "appearance", "2": "wealth", "3": "intelligence", "4": "height"}
    stat_display_names = {"appearance": "顏值", "wealth": "財富", "intelligence": "智慧", "height": "身高"}
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        term_width = os.get_terminal_size().columns
        
        title = "創建你的角色"
        lines = [f"你共有 {colors['system']}{points}{Style.RESET_ALL} 點可以分配。"]
        lines.append("-" * 20)
        for key, name in stat_display_names.items():
            lines.append(f"{name}: {stats[key]}{'cm' if key == 'height' else ''}")
        lines.append("-" * 20)
        lines.append("增加屬性：")
        lines.append(f"  {colors['prompt']}1. 顏值 (+1){Style.RESET_ALL}    {colors['prompt']}2. 財富 (+500){Style.RESET_ALL}")
        lines.append(f"  {colors['prompt']}3. 智慧 (+1){Style.RESET_ALL}    {colors['prompt']}4. 身高 (+5cm){Style.RESET_ALL}")
        lines.append("減少屬性：")
        lines.append(f"  {colors['prompt']}5. 顏值 (-1){Style.RESET_ALL}    {colors['prompt']}6. 財富 (-500){Style.RESET_ALL}")
        lines.append(f"  {colors['prompt']}7. 智慧 (-1){Style.RESET_ALL}    {colors['prompt']}8. 身高 (-5cm){Style.RESET_ALL}")
        lines.append("-" * 20)
        lines.append(f"{colors['system']}C. 完成創建{Style.RESET_ALL}")
        
        draw_box(title, lines, term_width)
        
        choice = input(colors["prompt"] + "> " + Style.RESET_ALL).lower()
        
        if choice == 'c':
            if points >= 0: break
        
        if choice in ['1', '2', '3', '4']: # Add points
            if points > 0:
                stat_to_change = stat_names[choice]
                if stat_to_change == 'height':
                    stats[stat_to_change] += 5
                elif stat_to_change == 'wealth':
                    stats[stat_to_change] += 500
                else:
                    stats[stat_to_change] += 1
                points -= 1
        elif choice in ['5', '6', '7', '8']: # Subtract points
            stat_to_change = {"5": "appearance", "6": "wealth", "7": "intelligence", "8": "height"}[choice]
            min_value = 1
            if stat_to_change == 'height':
                min_value = 165
            elif stat_to_change == 'wealth':
                min_value = 500 # Or some other minimum
            
            if stats[stat_to_change] > min_value:
                if stat_to_change == 'height':
                    stats[stat_to_change] -= 5
                elif stat_to_change == 'wealth':
                    stats[stat_to_change] -= 500
                else:
                    stats[stat_to_change] -= 1
                points += 1
    
    final_stats = {"inventory": [], "stamina": 100, "flags": []}
    final_stats.update(stats)
    return final_stats

# --- 遊戲主引擎 ---
def main():
    global player_stats, npc_stats, time_stats
    init(autoreset=True)
    try: sys.stdout.reconfigure(encoding='utf-8') # 強制設定輸出編碼
    except: pass
    
    current_scene_id = "start"
    info_message = ""
    loaded_game = False
    if os.path.exists(SAVE_FILE):
        if input(colors["system"] + "是否讀取之前的存檔？(y/n): " + Style.RESET_ALL).lower() == 'y':
            p, n, t, c = load_game()
            if p: 
                player_stats, npc_stats, time_stats, current_scene_id = p, n, t, c
                info_message = "讀取成功！"
                loaded_game = True
            else:
                info_message = "讀取失敗！將開始新遊戲。"
    
    if not loaded_game:
        player_stats = character_creation()

    term_width = os.get_terminal_size().columns

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')

        scene = story.get(current_scene_id)
        if not scene: print(f"錯誤：找不到場景 {current_scene_id}！"); break
        
        scene_type = scene.get("type")
        if scene_type == "router":
            next_scene_found = False
            for route in scene["routes"]:
                conditions_met = True
                conds = route["conditions"]
                if "npcs" in conds:
                    for npc_name, reqs in conds["npcs"].items():
                        if "min_affection" in reqs and npc_stats[npc_name]["affection"] < reqs["min_affection"]:
                            conditions_met = False; break
                    if not conditions_met: continue
                if "random_chance" in conds:
                    if random.random() >= conds["random_chance"]:
                        conditions_met = False
                if conditions_met:
                    current_scene_id = route["scene"]; next_scene_found = True; break
            if not next_scene_found: current_scene_id = scene["routes"][-1]["scene"]
            continue
        if scene_type == "final_eval":
            if npc_stats["girl"]["affection"] >= 15 and npc_stats["friend"]["affection"] > 0: current_scene_id = "ending_perfect"
            elif npc_stats["girl"]["affection"] >= 15 and npc_stats["friend"]["affection"] <= 0: current_scene_id = "ending_love_lost_friend"
            else: current_scene_id = "ending_scholar"
            continue
        if scene_type == "event_trigger":
            if scene["event_type"] == "exam":
                current_scene_id = scene["pass_scene"] if player_stats["intelligence"] >= scene["pass_threshold"] else scene["fail_scene"]
                continue

        time_str = f"📅 第 {time_stats['day']} 天, {PERIODS[time_stats['period_index']]}"
        draw_box("戀愛模擬器", [time_str], term_width)
        state_lines = prepare_state_lines(player_stats, npc_stats)
        draw_box("狀態", state_lines, term_width)
        if info_message: draw_box("通知", textwrap.wrap(info_message, width=int((term_width - 8)/2)), term_width); info_message = ""
        scene_lines = textwrap.wrap(scene["text"], width=int((term_width - 8)/2)) # 縮減寬度以容納中文字
        draw_box("劇情", scene_lines, term_width)

        if "choices" not in scene or not scene["choices"]: print("遊戲結束。"); break
        
        while True:
            choice_lines, available_choices = [], []
            for choice in scene["choices"]:
                reqs = choice.get("requirements", {})
                can_choose = True
                for stat, value in reqs.get("min_stats", {}).items():
                    if player_stats.get(stat, 0) < value: can_choose = False; choice_lines.append(f"{colors['locked']}(鎖定) {choice['text']} [需要 {stat}: {value}]"); break
                if not can_choose: continue
                for stat, value in reqs.get("max_stats", {}).items():
                    if player_stats.get(stat, 0) > value: can_choose = False; break
                if not can_choose: continue
                for npc, req in reqs.get("npcs", {}).items():
                    for req_type, value in req.items():
                        if req_type == "min_affection" and npc_stats[npc]["affection"] < value:
                            can_choose = False; choice_lines.append(f"{colors['locked']}(鎖定) {choice['text']} [需要 {npc} 好感度: {value}]"); break
                    if not can_choose: break
                if not can_choose: continue
                choice_lines.append(colors["prompt"] + choice['text']); available_choices.append(choice)

            choice_lines.append(colors["system"] + "---"); choice_lines.append(colors["system"] + "S.儲存 / L.讀取")
            draw_box("選擇", choice_lines, term_width)
            player_input = input(colors["prompt"] + "> " + Style.RESET_ALL).lower()

            if player_input == 's': save_game(player_stats, npc_stats, time_stats, current_scene_id); info_message = "遊戲已儲存！"; break
            if player_input == 'l':
                p, n, t, c = load_game(); 
                if p: player_stats, npc_stats, time_stats, current_scene_id = p, n, t, c; info_message = "讀取成功！"; break
                else: info_message = "讀取失敗！"; continue
            try:
                choice_num = int(player_input);
