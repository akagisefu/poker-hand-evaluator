from flask import Flask, jsonify, request, render_template
from collections import Counter
import random
from itertools import combinations # 組み合わせ計算に必要

app = Flask(__name__)

# --- 定数 ---
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
SUITS = ['H', 'D', 'S', 'C']
FULL_DECK = frozenset([r + s for r in RANKS for s in SUITS])
RANK_MAP = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
RANK_MAP_REV = {v: k for k, v in RANK_MAP.items()}

# 2-7SD ハンドカテゴリ (確率計算用)
# 注意: Bad Hand は Straight/Flush を含むため、個別のカテゴリより上に配置
HAND_CATEGORIES_27SD = [
    "7-High", "8-High", "9-High", "10-High", "J-High", "Q-High", "K-High", "A-High", # No Pair
    "One Pair", "Two Pair", "Three of a Kind",
    "Bad Hand (Straight/Flush)", # ストレートとフラッシュ
    "Full House", "Four of a Kind"
]
# 確率表示順序のためのマップ (カテゴリ名 -> ソート順)
HAND_CATEGORY_ORDER = {name: i for i, name in enumerate(HAND_CATEGORIES_27SD)}


# --- カード検証 ---
def validate_card(card):
    if len(card) not in [2,3]:
        return False
    rank = card[:-1].upper()
    suit = card[-1].upper()
    valid_ranks = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
    valid_suits = ['H','D','S','C']
    return rank in valid_ranks and suit in valid_suits

# evaluate_poker_hand は不要になったので削除 or コメントアウト
# def evaluate_poker_hand(cards): ...

# --- is_straight (変更なし) ---
def is_straight(ranks):
    # 2-7SDではAはハイカードとしてのみ扱うため、A-2-3-4-5はストレートではない
    # 5-4-3-2-Aのような並びもストレートではない
    # rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14} # グローバル定数を使用
    numeric_ranks = sorted([RANK_MAP[r] for r in set(ranks)]) # 重複を除いてソート

    if len(numeric_ranks) < 5: # ペアなどがある場合はストレートではない
        return False

    # A-2-3-4-5 (Aはハイなのでストレートではない) チェックは不要

    # 通常のストレートチェック
    is_straight_seq = all(numeric_ranks[i] == numeric_ranks[0] + i for i in range(len(numeric_ranks)))
    return is_straight_seq

# --- evaluate_27sd_hand (変更なし) ---
def evaluate_27sd_hand(cards):
    """2-7 Single Drawのハンドを評価する関数"""
    # 入力チェック
    if not cards or len(cards) != 5:
        # 評価不能なハンド（エラー処理を呼び出し元で行うか、ここで例外を発生させる）
        # ここでは仮に ('Invalid', []) を返す
        return 'Invalid', []

    ranks = [card[:-1].upper() for card in cards]
    suits = [card[-1].upper() for card in cards]

    rank_counts = Counter(ranks)
    suit_counts = Counter(suits)

    is_flush_hand = len(set(suits)) == 1
    is_straight_hand = is_straight(ranks)

    # ストレートやフラッシュは悪いハンド
    if is_straight_hand or is_flush_hand:
        hand_type = "Bad Hand (Straight/Flush)"
        # ハイカード順にランクを返す (Aが一番高い)
        # rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14} # グローバル定数を使用
        sorted_numeric_ranks = sorted([RANK_MAP[r] for r in ranks], reverse=True)
        return hand_type, sorted_numeric_ranks

    # ペア系の判定
    pairs = [rank for rank, count in rank_counts.items() if count == 2]
    threes = [rank for rank, count in rank_counts.items() if count == 3]
    fours = [rank for rank, count in rank_counts.items() if count == 4]

    # rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14} # グローバル定数を使用
    sorted_numeric_ranks = sorted([RANK_MAP[r] for r in ranks], reverse=True) # 降順ソート

    if fours:
        hand_type = "Four of a Kind"
    # elif threes and pairs: # フルハウスはストレート/フラッシュより強いので先に判定しない
    #     hand_type = "Full House"
    elif threes:
        hand_type = "Three of a Kind"
    elif len(pairs) == 2:
        hand_type = "Two Pair"
    elif pairs:
        hand_type = "One Pair"
    # フルハウスの判定をここで行う (ペア系よりは強い)
    elif threes and pairs: # この条件は実際には起こらない (threes か pairs で先に判定される)
         # 正しくは Counter の値で判定
         if sorted(rank_counts.values()) == [2, 3]:
              hand_type = "Full House"
         else: # ペアもストレートもフラッシュもない場合 -> ナンバーハンド
              hand_type = "No Pair" # または "High Card Hand"
    else:
         # ペアもストレートもフラッシュもない場合 -> ナンバーハンド
         hand_type = "No Pair" # または "High Card Hand"


    # 2-7SDでは、No Pairハンドが最も良く、その中で数字が小さいほど強い
    # 比較のために、ハンドタイプとソートされたランク（降順）を返す
    return hand_type, sorted_numeric_ranks


# --- ヘルパー関数 ---
def get_hand_category(hand_type, sorted_ranks):
    """評価結果から詳細なハンドカテゴリ名を返す"""
    if hand_type == "No Pair":
        # sorted_ranks は数値のリスト (降順)
        if not sorted_ranks: return "Invalid" # 空リスト対策
        high_card_rank = RANK_MAP_REV.get(sorted_ranks[0], '?') # 不明なランクは?
        return f"{high_card_rank}-High"
    # 他のタイプはそのまま返すか、必要なら詳細化
    return hand_type

def draw_cards(kept_cards, num_to_draw, available_deck):
    """指定された枚数のカードを利用可能なデッキからランダムに引く"""
    kept_cards_list = list(kept_cards) # setかもしれないのでリストに変換
    if num_to_draw <= 0:
        return kept_cards_list
    
    available_deck_list = list(available_deck)
    if len(available_deck_list) < num_to_draw:
        # ドローできない場合はエラーを示すか、不完全なハンドを返す
        # ここでは空リストを追加して返す（呼び出し元でlen==5をチェック）
        print(f"Warning: Not enough cards in deck to draw {num_to_draw}. Available: {len(available_deck_list)}")
        # return kept_cards_list # 不完全なハンドを返す
        # より明確にするため、Noneを返すか例外を投げるべきかもしれない
        return None # ドロー失敗を示す

    drawn_cards = random.sample(available_deck_list, num_to_draw)
    return kept_cards_list + drawn_cards


# --- 確率計算関数 ---
def calculate_draw_probabilities(kept_cards, available_deck, num_simulations=5000):
    """
    指定されたカードを持ち、残りをドローした場合の最終ハンドカテゴリ確率を計算する。
    """
    kept_cards_list = list(kept_cards) # setかもしれないのでリストに変換
    num_kept = len(kept_cards_list)

    if num_kept > 5: # エラーケース
         return {'error': 'Kept cards exceed 5'}
    if num_kept == 5: # すでに5枚持っている場合はドロー不要
        hand_type, sorted_ranks = evaluate_27sd_hand(kept_cards_list)
        if hand_type == 'Invalid':
             return {'error': 'Invalid hand provided'}
        category = get_hand_category(hand_type, sorted_ranks)
        # カテゴリが存在するか確認
        if category not in HAND_CATEGORIES_27SD:
             print(f"Warning: Unknown category '{category}' generated for hand {kept_cards_list}")
             # 不明なカテゴリは確率0として扱うか、エラーにするか
             # ここでは確率0とする
             probs = {cat: 0.0 for cat in HAND_CATEGORIES_27SD}
        else:
             probs = {cat: 1.0 if cat == category else 0.0 for cat in HAND_CATEGORIES_27SD}
        # 順序通りにソートして返す
        return dict(sorted(probs.items(), key=lambda item: HAND_CATEGORY_ORDER.get(item[0], float('inf'))))


    num_to_draw = 5 - num_kept
    category_counts = Counter()
    available_deck_list = list(available_deck)

    if len(available_deck_list) < num_to_draw:
        return {'error': f'Not enough cards in deck to draw {num_to_draw}'}

    # 全組み合わせを計算
    possible_draw_combinations = list(combinations(available_deck_list, num_to_draw))
    total_possible_outcomes = len(possible_draw_combinations)

    # シミュレーション回数を決定 (全組み合わせが少ない場合は全通り計算)
    actual_simulations = min(num_simulations, total_possible_outcomes)

    if actual_simulations == 0:
         return {'error': 'No possible draws'} # ドローできる組み合わせがない

    # サンプリングするか全通り計算するか
    if total_possible_outcomes > num_simulations * 1.5: # 全通りがシミュレーション回数よりかなり多い場合サンプリング
        simulation_combinations = random.sample(possible_draw_combinations, actual_simulations)
        total_outcomes_for_prob = actual_simulations # 確率計算の分母
        print(f"Calculating probabilities via sampling ({actual_simulations} simulations)")
    else:
        simulation_combinations = possible_draw_combinations
        total_outcomes_for_prob = total_possible_outcomes # 確率計算の分母
        print(f"Calculating probabilities via full enumeration ({total_possible_outcomes} combinations)")


    for drawn_cards in simulation_combinations:
        final_hand = kept_cards_list + list(drawn_cards)
        if len(final_hand) == 5:
            hand_type, sorted_ranks = evaluate_27sd_hand(final_hand)
            if hand_type == 'Invalid': continue # 評価不能なハンドはスキップ
            category = get_hand_category(hand_type, sorted_ranks)
            # カテゴリが存在するか確認
            if category in HAND_CATEGORIES_27SD:
                 category_counts[category] += 1
            else:
                 print(f"Warning: Unknown category '{category}' generated for hand {final_hand}")


    # 確率を計算 (カテゴリリストにあるもののみ)
    probabilities = {cat: category_counts[cat] / total_outcomes_for_prob for cat in HAND_CATEGORIES_27SD}
    # 順序通りにソートして返す
    return dict(sorted(probabilities.items(), key=lambda item: HAND_CATEGORY_ORDER.get(item[0], float('inf'))))


# --- 2-7SD ハンド比較関数 (変更なし) ---
def compare_27sd_hands(hand1_eval, hand2_eval):
    """
    2つの2-7SDハンド評価結果を比較し、hand1が勝てば1、hand2が勝てば-1、引き分けなら0を返す。
    hand_eval = (hand_type, sorted_numeric_ranks)
    2-7SDのランク (強い順): No Pair < One Pair < Two Pair < Three of a Kind < Bad Hand < Full House < Four of a Kind
    """
    type1, ranks1 = hand1_eval
    type2, ranks2 = hand2_eval

    # ハンドタイプが存在しない、またはランク情報がない場合は比較不能
    if not type1 or not ranks1 or not type2 or not ranks2:
        # エラーとして扱うか、特定の値を返す (例: 比較不能を示す None や 例外)
        # ここでは仮に 0 (引き分け扱い) とするが、要検討
        print(f"Warning: Cannot compare invalid hands: {hand1_eval} vs {hand2_eval}")
        return 0

    # ハンドタイプの強さ順序 (弱い方から強い方へ)
    # 注意: 2-7SDでは No Pair が最も強く、ペア系やストレート/フラッシュは弱い
    # HAND_CATEGORIES_27SD を利用 (ただし、これは表示用カテゴリ名)
    # 比較用の内部的な強さ順序を定義
    strength_map = {
        "No Pair": 0,
        "One Pair": 1,
        "Two Pair": 2,
        "Three of a Kind": 3,
        "Bad Hand (Straight/Flush)": 4, # ストレートとフラッシュは同等
        "Full House": 5,
        "Four of a Kind": 6,
        "Invalid": float('inf') # 評価不能なハンドは最弱
    }

    strength1 = strength_map.get(type1, float('inf'))
    strength2 = strength_map.get(type2, float('inf'))

    # ハンドタイプで比較 (数値が小さい方が強い)
    if strength1 < strength2:
        return 1 # hand1 の勝ち
    if strength1 > strength2:
        return -1 # hand2 の勝ち

    # --- ハンドタイプが同じ場合、ランクで比較 ---
    # No Pair の場合: 数字が小さい方が強い (例: 7-5-4-3-2 > 8-5-4-3-2)
    if type1 == "No Pair":
        # ranks1, ranks2 は数値のリスト (降順ソート済み)
        for r1, r2 in zip(ranks1, ranks2):
            if r1 < r2:
                return 1 # hand1 の勝ち (数字が小さい)
            if r1 > r2:
                return -1 # hand2 の勝ち (数字が小さい)
        return 0 # 引き分け

    # ペア系、ストレート/フラッシュの場合: 数字が大きい方が強い (通常のポーカーと同じ kicker 勝負)
    # (ただし、これらのハンドはNo Pairより弱い)
    else:
        # ranks1, ranks2 は数値のリスト (降順ソート済み)
        for r1, r2 in zip(ranks1, ranks2):
            if r1 > r2:
                return 1 # hand1 の勝ち (数字が大きい)
            if r1 < r2:
                return -1 # hand2 の勝ち (数字が大きい)
        return 0 # 引き分け


# --- 勝率計算関数 (ドロー考慮) ---
def calculate_post_draw_win_rate(p1_kept, p2_kept, num_simulations=10000):
    """
    各プレイヤーが指定カードを持ち、残りをドローした後の勝率を計算する。
    """
    p1_wins = 0
    p2_wins = 0
    ties = 0
    invalid_sims = 0

    p1_kept_set = set(p1_kept)
    p2_kept_set = set(p2_kept)
    initial_deck = FULL_DECK - p1_kept_set - p2_kept_set
    num_to_draw_p1 = 5 - len(p1_kept_set)
    num_to_draw_p2 = 5 - len(p2_kept_set)

    if len(initial_deck) < num_to_draw_p1 + num_to_draw_p2:
        return {'error': 'デッキの残りが少なく、シミュレーションできません'}

    print(f"Starting win rate simulation ({num_simulations} runs)...")
    print(f"P1 keeps: {p1_kept}, needs {num_to_draw_p1}")
    print(f"P2 keeps: {p2_kept}, needs {num_to_draw_p2}")
    print(f"Deck size for drawing: {len(initial_deck)}")


    for i in range(num_simulations):
        if i % (num_simulations // 10) == 0 and i > 0: # 進捗表示 (10%ごと)
             print(f"... {i}/{num_simulations} simulations done")

        available_deck_list = list(initial_deck) # 各シミュレーションでデッキをコピー

        # プレイヤー1のドロー
        p1_final_hand_list = draw_cards(p1_kept_set, num_to_draw_p1, available_deck_list)
        if p1_final_hand_list is None: # ドロー失敗
             invalid_sims += 1
             continue
        p1_final_hand = tuple(p1_final_hand_list) # 評価関数はリストを受け取るが、内部で使うためタプルに
        
        # P1が引いたカードをデッキから除く
        drawn_by_p1 = set(p1_final_hand) - p1_kept_set
        available_deck_after_p1_draw = initial_deck - drawn_by_p1

        # プレイヤー2のドロー
        p2_final_hand_list = draw_cards(p2_kept_set, num_to_draw_p2, available_deck_after_p1_draw)
        if p2_final_hand_list is None: # ドロー失敗
             invalid_sims += 1
             continue
        p2_final_hand = tuple(p2_final_hand_list)

        # ハンド評価と勝敗判定
        p1_eval = evaluate_27sd_hand(list(p1_final_hand)) # 評価関数はリストを期待
        p2_eval = evaluate_27sd_hand(list(p2_final_hand)) # 評価関数はリストを期待

        # 評価結果が不正でないかチェック
        if p1_eval[0] == 'Invalid' or p2_eval[0] == 'Invalid':
             invalid_sims += 1
             continue

        result = compare_27sd_hands(p1_eval, p2_eval)
        if result == 1:
            p1_wins += 1
        elif result == -1:
            p2_wins += 1
        else:
            ties += 1

    total_valid_simulations = p1_wins + p2_wins + ties
    print(f"Simulation finished. Valid runs: {total_valid_simulations}, Invalid runs: {invalid_sims}")

    if total_valid_simulations == 0:
        # 有効なシミュレーションが0回の場合
        if invalid_sims > 0:
             return {'error': f'All simulations resulted in invalid draws ({invalid_sims} attempts). Check deck logic.'}
        else:
             return {'player1_wins': 0, 'player2_wins': 0, 'ties': 0, 'simulations': 0}


    return {
        'player1_wins': p1_wins / total_valid_simulations,
        'player2_wins': p2_wins / total_valid_simulations,
        'ties': ties / total_valid_simulations,
        'simulations': total_valid_simulations
    }


# --- 新しいAPIエンドポイント ---
@app.route('/api/calculate', methods=['POST'])
def calculate_api():
    try:
        data = request.json
        p1_cards_input = data.get('player1_cards', [])
        p2_cards_input = data.get('player2_cards', [])

        # 入力バリデーション
        if len(p1_cards_input) > 5 or len(p2_cards_input) > 5:
            return jsonify({'error': '各プレイヤーの手札は最大5枚までです'}), 400

        # frozenset に変換して処理
        p1_cards = frozenset(p1_cards_input)
        p2_cards = frozenset(p2_cards_input)

        all_selected_cards = p1_cards.union(p2_cards)
        invalid_cards = [card for card in all_selected_cards if not validate_card(card)]
        if invalid_cards:
            return jsonify({'error': f'無効なカード形式: {", ".join(invalid_cards)}'}), 400

        if len(all_selected_cards) != len(p1_cards) + len(p2_cards):
             # このチェックは frozenset を使っているので不要 (重複は自動で除去される)
             # ただし、p1 と p2 で同じカードが選択された場合のチェックは必要
             if not p1_cards.isdisjoint(p2_cards):
                  return jsonify({'error': 'プレイヤー間で同じカードが選択されています'}), 400


        # デッキ準備 (確率計算用と勝率計算用で共有可能)
        deck_minus_selection = FULL_DECK - all_selected_cards

        # ハンド確率計算
        print("Calculating P1 probabilities...")
        p1_probabilities = calculate_draw_probabilities(p1_cards, deck_minus_selection)
        print("Calculating P2 probabilities...")
        p2_probabilities = calculate_draw_probabilities(p2_cards, deck_minus_selection)

        # 勝率計算 (ドロー考慮)
        print("Calculating win rates...")
        win_rates = calculate_post_draw_win_rate(p1_cards, p2_cards) # 関数には set を渡す

        # --- 結果の整形 ---
        # ドロー後のハンド例を一つ生成 (表示用)
        p1_final_hand_example_list = draw_cards(p1_cards, 5 - len(p1_cards), deck_minus_selection)
        if p1_final_hand_example_list is None: p1_final_hand_example_list = list(p1_cards) # ドロー失敗時は保持カードのみ

        deck_after_p1_draw = deck_minus_selection - (set(p1_final_hand_example_list) - p1_cards)
        p2_final_hand_example_list = draw_cards(p2_cards, 5 - len(p2_cards), deck_after_p1_draw)
        if p2_final_hand_example_list is None: p2_final_hand_example_list = list(p2_cards) # ドロー失敗時は保持カードのみ

        # 評価とハンド名取得 (5枚揃っているか確認)
        p1_final_eval = evaluate_27sd_hand(p1_final_hand_example_list) if len(p1_final_hand_example_list) == 5 else ('Invalid', [])
        p2_final_eval = evaluate_27sd_hand(p2_final_hand_example_list) if len(p2_final_hand_example_list) == 5 else ('Invalid', [])

        p1_hand_name = get_hand_category(p1_final_eval[0], p1_final_eval[1]) if p1_final_eval[0] != 'Invalid' else "N/A"
        p2_hand_name = get_hand_category(p2_final_eval[0], p2_final_eval[1]) if p2_final_eval[0] != 'Invalid' else "N/A"

        # ハンド例をソートして見やすくする
        p1_final_hand_sorted = sorted(p1_final_hand_example_list, key=lambda c: RANK_MAP.get(c[:-1], 0))
        p2_final_hand_sorted = sorted(p2_final_hand_example_list, key=lambda c: RANK_MAP.get(c[:-1], 0))


        response_data = {
            'player1': {
                'final_hand': p1_final_hand_sorted,
                'hand_name': p1_hand_name,
                'probabilities': p1_probabilities # エラーが含まれる可能性あり
            },
            'player2': {
                'final_hand': p2_final_hand_sorted,
                'hand_name': p2_hand_name,
                'probabilities': p2_probabilities # エラーが含まれる可能性あり
            },
            'win_rates': win_rates # エラーが含まれる可能性あり
        }
        # エラーがあればトップレベルにも追加 (フロントで扱いやすくするため)
        if isinstance(p1_probabilities, dict) and 'error' in p1_probabilities:
             response_data['error'] = response_data.get('error', '') + f" P1 Prob Error: {p1_probabilities['error']}"
        if isinstance(p2_probabilities, dict) and 'error' in p2_probabilities:
             response_data['error'] = response_data.get('error', '') + f" P2 Prob Error: {p2_probabilities['error']}"
        if isinstance(win_rates, dict) and 'error' in win_rates:
             response_data['win_rate_error'] = win_rates['error'] # これは専用フィールドに


        return jsonify(response_data)

    except Exception as e:
        # より詳細なエラーログをサーバー側に出力
        import traceback
        print("--- Error in /api/calculate ---")
        traceback.print_exc()
        print("--- End Error ---")
        return jsonify({'error': f'サーバー内部で予期せぬエラーが発生しました: {type(e).__name__}'}), 500


# --- index ルート (変更なし) ---
@app.route('/')
def index():
    return render_template('index.html')

# --- 古い /api/evaluate は削除 ---
# @app.route('/api/evaluate', methods=['POST']) ...

# --- サーバー起動 ---
if __name__ == '__main__':
    # 本番環境では gunicorn を使うため、app.run は開発時のみ
    # Render などでは Start Command で gunicorn を指定する
    app.run(debug=True) # 開発時は True のまま
