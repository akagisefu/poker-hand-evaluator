from flask import Flask, jsonify, request, render_template
from collections import Counter
import random # 勝率計算のために追加
from itertools import combinations # デッキ生成用

app = Flask(__name__)

# --- カード検証 ---
def validate_card(card):
    if len(card) not in [2,3]:
        return False
    rank = card[:-1].upper()
    suit = card[-1].upper()
    valid_ranks = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
    valid_suits = ['H','D','S','C']
    return rank in valid_ranks and suit in valid_suits

def evaluate_poker_hand(cards):
    ranks = [card[:-1].upper() for card in cards]
    suits = [card[-1].upper() for card in cards]
    
    rank_counts = Counter(ranks)
    suit_counts = Counter(suits)
    
    # ポーカー役判定ロジック
    if len(set(suits)) == 1 and set(ranks) == {'10','J','Q','K','A'}:
        return 'ロイヤルストレートフラッシュ'
    
    if len(set(suits)) == 1 and is_straight(ranks):
        return 'ストレートフラッシュ'
    
    if 4 in rank_counts.values():
        return 'フォーカード'
    
    if sorted(rank_counts.values()) == [2,3]:
        return 'フルハウス'
    
    if len(set(suits)) == 1:
        return 'フラッシュ'
    
    if is_straight(ranks):
        return 'ストレート'
    
    if 3 in rank_counts.values():
        return 'スリーカード'
    
    if list(rank_counts.values()).count(2) == 2:
        return 'ツーペア'
    
    if 2 in rank_counts.values():
        return 'ワンペア'
    
    return 'ハイカード'

def is_straight(ranks):
    # 2-7SDではAはハイカードとしてのみ扱うため、A-2-3-4-5はストレートではない
    # 5-4-3-2-Aのような並びもストレートではない
    rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    numeric_ranks = sorted([rank_map[r] for r in set(ranks)]) # 重複を除いてソート

    if len(numeric_ranks) < 5: # ペアなどがある場合はストレートではない
        return False

    # A-2-3-4-5 (Aはハイなのでストレートではない) チェックは不要

    # 通常のストレートチェック
    is_straight_seq = all(numeric_ranks[i] == numeric_ranks[0] + i for i in range(len(numeric_ranks)))
    return is_straight_seq

def evaluate_27sd_hand(cards):
    """2-7 Single Drawのハンドを評価する関数"""
    ranks = [card[:-1].upper() for card in cards]
    suits = [card[-1].upper() for card in cards]

    rank_counts = Counter(ranks)
    suit_counts = Counter(suits)

    is_flush_hand = len(set(suits)) == 1
    is_straight_hand = is_straight(ranks)

    # ストレートやフラッシュは悪いハンド
    if is_straight_hand or is_flush_hand:
        # ストレートフラッシュやロイヤルは考慮不要 (通常のポーカーとは逆)
        # 単純にストレートかフラッシュがあれば、それはペアなどより悪いハンドとして扱うことが多いが、
        # ここではまず役の種類を返すことにする。比較ロジックは別途必要。
        # 簡単のため、ここでは「悪いハンド」としてマークするだけにする
        # より詳細な比較のためには、ハイカード情報も保持する必要がある
        hand_type = "Bad Hand (Straight/Flush)"
        # ハイカード順にランクを返す (Aが一番高い)
        rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        sorted_numeric_ranks = sorted([rank_map[r] for r in ranks], reverse=True)
        return hand_type, sorted_numeric_ranks

    # ペア系の判定
    pairs = [rank for rank, count in rank_counts.items() if count == 2]
    threes = [rank for rank, count in rank_counts.items() if count == 3]
    fours = [rank for rank, count in rank_counts.items() if count == 4]

    rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    sorted_numeric_ranks = sorted([rank_map[r] for r in ranks], reverse=True) # 降順ソート

    if fours:
        hand_type = "Four of a Kind"
    elif threes and pairs:
        hand_type = "Full House"
    elif threes:
        hand_type = "Three of a Kind"
    elif len(pairs) == 2:
        hand_type = "Two Pair"
    elif pairs:
        hand_type = "One Pair"
    else:
        # ペアもストレートもフラッシュもない場合 -> ナンバーハンド
        hand_type = "No Pair" # または "High Card Hand"

    # 2-7SDでは、No Pairハンドが最も良く、その中で数字が小さいほど強い
    # 比較のために、ハンドタイプとソートされたランク（降順）を返す
    return hand_type, sorted_numeric_ranks

# --- 2-7SD ハンド比較関数 ---
def compare_27sd_hands(hand1_eval, hand2_eval):
    """
    2つの2-7SDハンド評価結果を比較し、hand1が勝てば1、hand2が勝てば-1、引き分けなら0を返す。
    hand_eval = (hand_type, sorted_numeric_ranks)
    2-7SDのランク: No Pair < One Pair < Two Pair < Three of a Kind < Straight/Flush < Full House < Four of a Kind
    No Pair同士はハイカード（数字が小さい方が強い）で比較。
    """
    type1, ranks1 = hand1_eval
    type2, ranks2 = hand2_eval

    # ハンドタイプの強さ順序 (弱い方から強い方へ)
    # 注意: 2-7SDでは No Pair が最も強く、ペア系やストレート/フラッシュは弱い
    hand_strength_order = [
        "No Pair",
        "One Pair",
        "Two Pair",
        "Three of a Kind",
        "Bad Hand (Straight/Flush)", # ストレートとフラッシュは同等に扱う
        "Full House",
        "Four of a Kind"
    ]

    # ハンドタイプを数値に変換 (リストのインデックスを使用。小さいほど強い)
    try:
        strength1 = hand_strength_order.index(type1)
    except ValueError:
        strength1 = float('inf') # 不明なタイプは最弱扱い（エラーケース）
    try:
        strength2 = hand_strength_order.index(type2)
    except ValueError:
        strength2 = float('inf')

    # ハンドタイプで比較 (数値が小さい方が強い)
    if strength1 < strength2:
        return 1 # hand1 の勝ち
    if strength1 > strength2:
        return -1 # hand2 の勝ち

    # ハンドタイプが同じ場合、ランクで比較
    # No Pair の場合: 数字が小さい方が強い (例: 7-5-4-3-2 > 8-5-4-3-2)
    if type1 == "No Pair":
        for r1, r2 in zip(ranks1, ranks2): # ランクは降順ソート済み
            if r1 < r2:
                return 1 # hand1 の勝ち
            if r1 > r2:
                return -1 # hand2 の勝ち
        return 0 # 引き分け

    # ペア系、ストレート/フラッシュの場合: 数字が大きい方が強い (通常のポーカーと同じ)
    # (ただし、これらのハンドはNo Pairより弱い)
    else:
        for r1, r2 in zip(ranks1, ranks2): # ランクは降順ソート済み
            if r1 > r2:
                return 1 # hand1 の勝ち
            if r1 < r2:
                return -1 # hand2 の勝ち
        return 0 # 引き分け

# --- 勝率計算関数 (モンテカルロ法) ---
def calculate_win_rate(my_cards, num_simulations=10000):
    """
    与えられた手札 (my_cards) の2-7SDにおける勝率をモンテカルロ法で概算する。
    """
    wins = 0
    ties = 0
    losses = 0

    # デッキの準備
    ranks = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
    suits = ['H','D','S','C']
    deck = [r + s for r in ranks for s in suits]

    # 自分の手札をデッキから削除
    remaining_deck = [card for card in deck if card not in my_cards]

    if len(remaining_deck) < 5:
        return {'error': 'デッキの残りが少なく、シミュレーションできません'} # エラーケース

    my_hand_eval = evaluate_27sd_hand(my_cards)

    for _ in range(num_simulations):
        # 相手の手札をランダムに選択
        opponent_cards = random.sample(remaining_deck, 5)
        opponent_hand_eval = evaluate_27sd_hand(opponent_cards)

        # ハンド比較
        result = compare_27sd_hands(my_hand_eval, opponent_hand_eval)

        if result == 1:
            wins += 1
        elif result == -1:
            losses += 1
        else:
            ties += 1

    total_simulations = wins + losses + ties
    if total_simulations == 0:
        return {'win_rate': 0, 'tie_rate': 0, 'loss_rate': 0, 'simulations': 0}

    win_rate = wins / total_simulations
    tie_rate = ties / total_simulations
    loss_rate = losses / total_simulations

    return {
        'win_rate': win_rate,
        'tie_rate': tie_rate,
        'loss_rate': loss_rate,
        'simulations': total_simulations
    }


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    try:
        data = request.json
        cards = data.get('cards', [])
        
        if len(cards) != 5:
            return jsonify({'error': '5枚のカードを入力してください'}), 400
            
        invalid_cards = [card for card in cards if not validate_card(card)]
        if invalid_cards:
            return jsonify({'error': f'無効なカード形式: {", ".join(invalid_cards)}'}), 400

        # 2-7SDの評価関数を呼び出す
        hand_type, sorted_ranks = evaluate_27sd_hand(cards)

        # ランクと数値のマッピング (ソート用と逆引き用)
        rank_map_sort = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        rank_map_rev = {v: k for k, v in rank_map_sort.items()}
        rank_str = [rank_map_rev[r] for r in sorted_ranks]

        # 2-7SDのハンド名を生成 (例: "7-5-4-3-2", "King High", "Pair of Aces")
        if hand_type == "No Pair":
            # No Pairの場合、ハイカードでハンド名を表現 (例: 7-5-4-3-2)
            hand_name = "-".join(rank_str)
        elif hand_type == "One Pair":
            pair_rank = [r for r, c in Counter(rank_str).items() if c == 2][0]
            kickers = sorted([r for r in rank_str if r != pair_rank], key=lambda x: rank_map_sort[x], reverse=True)
            hand_name = f"Pair of {pair_rank}s ({'-'.join(kickers)} kickers)"
        elif hand_type == "Two Pair":
             pairs_ranks = sorted([r for r, c in Counter(rank_str).items() if c == 2], key=lambda x: rank_map_sort[x], reverse=True)
             kicker = [r for r in rank_str if rank_str.count(r) == 1][0]
             hand_name = f"Two Pair, {pairs_ranks[0]}s and {pairs_ranks[1]}s ({kicker} kicker)"
        elif hand_type == "Three of a Kind":
            three_rank = [r for r, c in Counter(rank_str).items() if c == 3][0]
            kickers = sorted([r for r in rank_str if r != three_rank], key=lambda x: rank_map_sort[x], reverse=True)
            hand_name = f"Three of a Kind, {three_rank}s ({'-'.join(kickers)} kickers)"
        elif hand_type == "Bad Hand (Straight/Flush)":
             # ストレートやフラッシュの場合もハイカードで表現
             hand_name = f"{hand_type}: {'-'.join(rank_str)}"
        elif hand_type == "Full House":
            three_rank = [r for r, c in Counter(rank_str).items() if c == 3][0]
            pair_rank = [r for r, c in Counter(rank_str).items() if c == 2][0]
            hand_name = f"Full House, {three_rank}s full of {pair_rank}s"
        elif hand_type == "Four of a Kind":
            four_rank = [r for r, c in Counter(rank_str).items() if c == 4][0]
            kicker = [r for r in rank_str if r != four_rank][0]
            hand_name = f"Four of a Kind, {four_rank}s ({kicker} kicker)"
        else:
             hand_name = hand_type # フォールバック

        # 勝率計算を実行
        win_rate_result = calculate_win_rate(cards) # num_simulationsはデフォルト値を使用

        response_data = {
            'hand_type': hand_type,
            'sorted_ranks': rank_str,
            'hand_name': hand_name,
            'details': f'入力カード: {", ".join(cards)}',
        }
        # 勝率計算結果を追加 (エラーがあればエラーメッセージを、なければ勝率などを追加)
        if 'error' in win_rate_result:
             response_data['win_rate_error'] = win_rate_result['error']
        else:
             response_data.update(win_rate_result) # win_rate, tie_rateなどを辞書に追加

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
