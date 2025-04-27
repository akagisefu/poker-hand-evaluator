const ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'];
const suits = ['H', 'D', 'S', 'C']; // ハート, ダイヤ, スペード, クラブ
const deck = [];
suits.forEach(suit => {
    ranks.forEach(rank => {
        deck.push(rank + suit);
    });
});

let selectedCardsP1 = [];
let selectedCardsP2 = [];

// カードボタン要素を作成する関数
function createCardElement(card, playerId) {
    const cardButton = document.createElement('button');
    cardButton.classList.add('card-button'); // 新しいクラス名
    cardButton.dataset.card = card; // カード情報をdata属性に保持
    cardButton.textContent = card; // ボタンのテキストをカード名に設定

    cardButton.addEventListener('click', () => handleCardClick(card, playerId));
    return cardButton;
}

// カード選択ロジック (クラス名を .card から .card-button に変更)
function handleCardClick(card, playerId) {
    const playerSelector = document.getElementById(`player${playerId}-selector`);
    const cardElement = playerSelector.querySelector(`.card-button[data-card="${card}"]`); // クラス名変更
    const otherPlayerId = playerId === 1 ? 2 : 1;
    const otherPlayerSelected = playerId === 1 ? selectedCardsP2 : selectedCardsP1;
    let currentSelected = playerId === 1 ? selectedCardsP1 : selectedCardsP2;

    // 相手が選択中のカードは選択不可
    if (otherPlayerSelected.includes(card)) {
        alert(`プレイヤー${otherPlayerId}が選択中のカードです。`);
        return;
    }

    const cardIndex = currentSelected.indexOf(card);

    if (cardIndex > -1) {
        // すでに選択されている場合は解除
        currentSelected.splice(cardIndex, 1);
        cardElement.classList.remove('selected');
    } else {
        // 新しく選択する場合 (5枚まで)
        if (currentSelected.length < 5) {
            currentSelected.push(card);
            cardElement.classList.add('selected');
        } else {
            alert('選択できるカードは5枚までです。');
        }
    }

    // 選択中カード表示を更新
    updateSelectedDisplay(playerId);
    // 相手のセレクターで同じカードを無効化/有効化
    updateOpponentSelector(card, playerId, cardIndex === -1);
}

// 選択中カード表示を更新
function updateSelectedDisplay(playerId) {
    const selectedDisplay = document.getElementById(`player${playerId}-selected`);
    const currentSelected = playerId === 1 ? selectedCardsP1 : selectedCardsP2;
    selectedDisplay.innerHTML = `選択中のカード (${currentSelected.length}/5枚): ${currentSelected.join(', ')}`;
    // ここで選択中カードの画像を表示するようにしても良い
}

// 相手プレイヤーのカードセレクターの状態を更新 (クラス名を .card から .card-button に変更)
function updateOpponentSelector(card, selectingPlayerId, isSelected) {
    const otherPlayerId = selectingPlayerId === 1 ? 2 : 1;
    const otherPlayerSelector = document.getElementById(`player${otherPlayerId}-selector`);
    const otherCardElement = otherPlayerSelector.querySelector(`.card-button[data-card="${card}"]`); // クラス名変更
    if (otherCardElement) {
        if (isSelected) {
            otherCardElement.classList.add('disabled'); // 相手が選択したので無効化
            otherCardElement.disabled = true; // ボタンを無効化
        } else {
            otherCardElement.classList.remove('disabled'); // 選択解除されたので有効化
            otherCardElement.disabled = false; // ボタンを有効化
        }
    }
}


// カードセレクターを描画
function renderCardSelectors() {
    const selectorP1 = document.getElementById('player1-selector');
    const selectorP2 = document.getElementById('player2-selector');
    selectorP1.innerHTML = ''; // 初期化
    selectorP2.innerHTML = ''; // 初期化

    deck.forEach(card => {
        selectorP1.appendChild(createCardElement(card, 1));
        selectorP2.appendChild(createCardElement(card, 2));
    });
}

// 勝率計算APIを呼び出す関数
async function calculateWinRate() {
    const resultDisplay = document.getElementById('result-display');
    const errorMessageEl = document.getElementById('error-message');
    const calcErrorEl = document.getElementById('calc-error');

    // 結果表示をリセット & 非表示
    resultDisplay.style.display = 'none';
    errorMessageEl.style.display = 'none';
    calcErrorEl.style.display = 'none';
    resetResultFields(); // 各フィールドを '-' に戻す

    // 選択されたカードが0枚の場合はエラー
    if (selectedCardsP1.length === 0 && selectedCardsP2.length === 0) {
        errorMessageEl.textContent = 'エラー: 少なくともどちらか一方のプレイヤーがカードを選択してください。';
        errorMessageEl.style.display = 'block';
        return;
    }

    try {
        // バックエンドAPIのパスを修正 (例: /api/calculate)
        const response = await fetch('/api/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                player1_cards: selectedCardsP1,
                player2_cards: selectedCardsP2
            })
        });

        const data = await response.json();

        if (!response.ok || data.error) {
            errorMessageEl.textContent = `エラー: ${data.error || response.statusText}`;
            errorMessageEl.style.display = 'block';
        } else {
            // 結果を表示
            displayResults(data);
            resultDisplay.style.display = 'block';
        }

    } catch (error) {
        errorMessageEl.textContent = `通信エラー: ${error.message}`;
        errorMessageEl.style.display = 'block';
    }
}

// 結果フィールドをリセット
function resetResultFields() {
    document.getElementById('p1-final-hand').textContent = '-';
    document.getElementById('p1-hand-name').textContent = '-';
    document.getElementById('p1-hand-probs').innerHTML = '';
    document.getElementById('p2-final-hand').textContent = '-';
    document.getElementById('p2-hand-name').textContent = '-';
    document.getElementById('p2-hand-probs').innerHTML = '';
    document.getElementById('p1-win-rate').textContent = '-';
    document.getElementById('tie-rate').textContent = '-';
    document.getElementById('p2-win-rate').textContent = '-';
    document.getElementById('simulations').textContent = '-';
    document.getElementById('calc-error').textContent = '';
    document.getElementById('calc-error').style.display = 'none';
}

// APIからの結果を表示
function displayResults(data) {
    // プレイヤー1の結果
    if (data.player1) {
        document.getElementById('p1-final-hand').textContent = data.player1.final_hand ? data.player1.final_hand.join(', ') : 'N/A';
        document.getElementById('p1-hand-name').textContent = data.player1.hand_name || '-';
        const p1ProbsList = document.getElementById('p1-hand-probs');
        p1ProbsList.innerHTML = ''; // Clear previous results
        if (data.player1.probabilities) {
            for (const [hand, prob] of Object.entries(data.player1.probabilities)) {
                const li = document.createElement('li');
                li.textContent = `${hand}: ${(prob * 100).toFixed(2)}%`;
                p1ProbsList.appendChild(li);
            }
        }
    }

    // プレイヤー2の結果
    if (data.player2) {
        document.getElementById('p2-final-hand').textContent = data.player2.final_hand ? data.player2.final_hand.join(', ') : 'N/A';
        document.getElementById('p2-hand-name').textContent = data.player2.hand_name || '-';
        const p2ProbsList = document.getElementById('p2-hand-probs');
        p2ProbsList.innerHTML = ''; // Clear previous results
        if (data.player2.probabilities) {
            for (const [hand, prob] of Object.entries(data.player2.probabilities)) {
                const li = document.createElement('li');
                li.textContent = `${hand}: ${(prob * 100).toFixed(2)}%`;
                p2ProbsList.appendChild(li);
            }
        }
    }

    // 勝率結果
    if (data.win_rate_error) {
        document.getElementById('calc-error').textContent = `勝率計算エラー: ${data.win_rate_error}`;
        document.getElementById('calc-error').style.display = 'block';
    } else if (data.win_rates) {
        document.getElementById('p1-win-rate').textContent = (data.win_rates.player1_wins * 100).toFixed(2);
        document.getElementById('tie-rate').textContent = (data.win_rates.ties * 100).toFixed(2);
        // P2の勝率は100 - P1勝率 - 引き分け率 で計算も可能だが、APIから直接受け取る方が確実
        document.getElementById('p2-win-rate').textContent = (data.win_rates.player2_wins * 100).toFixed(2);
        document.getElementById('simulations').textContent = data.win_rates.simulations || '-';
    }
}


// ページ読み込み完了時にカードセレクターを描画
window.addEventListener('DOMContentLoaded', renderCardSelectors);
