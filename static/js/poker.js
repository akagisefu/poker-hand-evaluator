async function evaluateHand() {
    const input = document.getElementById('cards-input').value.trim();
    const cards = input.split(/\s+/); // スペース区切りでカードを配列に

    // 結果表示要素を取得
    const handNameEl = document.getElementById('hand-name');
    const handTypeEl = document.getElementById('hand-type');
    const sortedRanksEl = document.getElementById('sorted-ranks');
    const winRateEl = document.getElementById('win-rate');
    const tieRateEl = document.getElementById('tie-rate');
    const lossRateEl = document.getElementById('loss-rate');
    const simulationsEl = document.getElementById('simulations');
    const winRateErrorEl = document.getElementById('win-rate-error');
    const errorMessageEl = document.getElementById('error-message');
    const resultDetailsEl = document.getElementById('result-details');

    // 結果表示をリセット
    handNameEl.textContent = '-';
    handTypeEl.textContent = '-';
    sortedRanksEl.textContent = '-';
    winRateEl.textContent = '-';
    tieRateEl.textContent = '-';
    lossRateEl.textContent = '-';
    simulationsEl.textContent = '-';
    winRateErrorEl.textContent = '';
    winRateErrorEl.style.display = 'none';
    errorMessageEl.textContent = '';
    errorMessageEl.style.display = 'none';
    resultDetailsEl.style.display = 'none'; // 最初は詳細を隠す

    try {
        const response = await fetch('/api/evaluate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            // 空白で分割したカード配列を送信
            body: JSON.stringify({ cards: cards.filter(c => c) }) // 空の要素を除去
        });

        const data = await response.json();

        if (!response.ok || data.error) {
            // APIからのエラー (入力形式エラーなど)
            errorMessageEl.textContent = `エラー: ${data.error || response.statusText}`;
            errorMessageEl.style.display = 'block';
        } else {
            // 正常なレスポンス
            handNameEl.textContent = data.hand_name || '-';
            handTypeEl.textContent = data.hand_type || '-';
            sortedRanksEl.textContent = data.sorted_ranks ? data.sorted_ranks.join(', ') : '-';

            if (data.win_rate_error) {
                // 勝率計算エラー
                winRateErrorEl.textContent = `勝率計算エラー: ${data.win_rate_error}`;
                winRateErrorEl.style.display = 'block';
                // 勝率関連のフィールドは '-' のままにする
                winRateEl.textContent = '-';
                tieRateEl.textContent = '-';
                lossRateEl.textContent = '-';
                simulationsEl.textContent = '-';
            } else if (data.win_rate !== undefined) {
                // 勝率計算成功
                winRateEl.textContent = (data.win_rate * 100).toFixed(2); // %表示、小数点以下2桁
                tieRateEl.textContent = (data.tie_rate * 100).toFixed(2);
                lossRateEl.textContent = (data.loss_rate * 100).toFixed(2);
                simulationsEl.textContent = data.simulations || '-';
                winRateErrorEl.style.display = 'none'; // エラーメッセージを隠す
            } else {
                // 勝率データがない場合 (古いAPIなど、念のため)
                winRateEl.textContent = '-';
                tieRateEl.textContent = '-';
                lossRateEl.textContent = '-';
                simulationsEl.textContent = '-';
            }

            resultDetailsEl.style.display = 'block'; // 結果詳細を表示
            errorMessageEl.style.display = 'none'; // エラーメッセージを隠す
        }

    } catch (error) {
        // 通信エラーなど
        errorMessageEl.textContent = `通信エラー: ${error.message}`;
        errorMessageEl.style.display = 'block';
        resultDetailsEl.style.display = 'none';
    }
}
