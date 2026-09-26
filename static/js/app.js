let pollTimer = null;
let selectedSymbol = 'BTCUSDT';
let renderedSymbols = '';

document.addEventListener('DOMContentLoaded', () => {
    fetchStatus();
    fetchTradeHistory();
    pollTimer = setInterval(fetchStatus, 3000);
});

function getTradingViewSymbol(sym) {
    if (!sym) return 'KUCOIN:BTCUSDT';
    let clean = sym.toUpperCase().replace('/', '').replace('-', '').replace('KUCOIN:', '');
    let coin = clean.replace('IDR', '').replace('USDT', '');
    return 'KUCOIN:' + coin + 'USDT';
}

function selectCoin(sym) {
    selectedSymbol = sym.toUpperCase().replace('/', '').replace('-', '');
    const tvSym = getTradingViewSymbol(selectedSymbol);
    const baseCoin = selectedSymbol.replace('IDR', '').replace('USDT', '');
    
    // Update active coin pill UI
    document.querySelectorAll('.coin-pill').forEach(btn => {
        if (btn.innerText.includes(baseCoin)) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Sync Chart Dropdown and TradingView Widget
    const chartSelect = document.getElementById('select-chart-symbol');
    if (chartSelect) {
        chartSelect.value = tvSym;
    }
    if (typeof updateChartSymbol === 'function') {
        updateChartSymbol(tvSym);
    }

    // Immediately fetch updated HUD & AI for selected coin
    fetchStatus();
}

function renderCoinPills(symbols) {
    const container = document.getElementById('coin-pills-container');
    if (!container) return;
    
    const key = symbols.join(',');
    if (key === renderedSymbols) {
        // Just update active class
        document.querySelectorAll('.coin-pill').forEach(btn => {
            if (btn.innerText.includes(selectedSymbol)) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        return;
    }

    renderedSymbols = key;
    let html = '';
    symbols.forEach(sym => {
        const isActive = (sym === selectedSymbol) ? 'active' : '';
        html += `
            <button type="button" class="coin-pill ${isActive}" onclick="selectCoin('${sym}')">
                <i class="bi bi-coin text-warning" style="font-size: 0.75rem;"></i>${sym}
            </button>
        `;
    });
    container.innerHTML = html;
}

async function fetchStatus() {
    try {
        const tf = document.getElementById('cfg-timeframe') ? document.getElementById('cfg-timeframe').value : '5m';
        const res = await fetch(`/api/status?symbol=${selectedSymbol}&timeframe=${tf}`);
        const data = await res.json();
        
        // 1. Bot Status Badge, Pulse Dot & Dynamic Action Buttons
        const statusBadge = document.getElementById('bot-status-badge');
        const btnStart = document.getElementById('btn-start');
        const btnStop = document.getElementById('btn-stop');

        if (data.bot_running) {
            statusBadge.className = 'badge bg-dark border border-success text-emerald px-3 py-2 rounded-pill d-flex align-items-center gap-2 shadow-sm';
            statusBadge.innerHTML = '<span class="pulse-dot pulse-dot-active"></span> <strong class="text-emerald">RUNNING</strong>';

            if (btnStart) {
                btnStart.disabled = true;
                btnStart.className = 'btn btn-running flex-fill py-2 rounded-3';
                btnStart.innerHTML = '<span class="spinner-grow spinner-grow-sm me-1 text-success"></span> BOT AKTIF';
            }
            if (btnStop) {
                btnStop.disabled = false;
                btnStop.className = 'btn btn-stop-active flex-fill py-2 rounded-3';
                btnStop.innerHTML = '<i class="bi bi-stop-fill me-1"></i> STOP BOT';
            }
        } else {
            statusBadge.className = 'badge bg-dark border border-danger text-rose px-3 py-2 rounded-pill d-flex align-items-center gap-2 shadow-sm';
            statusBadge.innerHTML = '<span class="pulse-dot pulse-dot-stopped"></span> <strong class="text-rose">STOPPED</strong>';

            if (btnStart) {
                btnStart.disabled = false;
                btnStart.className = 'btn btn-start-pro flex-fill py-2 rounded-3';
                btnStart.innerHTML = '<i class="bi bi-play-fill me-1"></i> START BOT';
            }
            if (btnStop) {
                btnStop.disabled = true;
                btnStop.className = 'btn btn-stop-disabled flex-fill py-2 rounded-3';
                btnStop.innerHTML = '<i class="bi bi-stop-fill me-1"></i> STOP';
            }
        }

        // 2. License Badge
        const licBadge = document.getElementById('license-badge');
        if (data.license_valid) {
            licBadge.className = 'badge bg-success-subtle text-success border border-success px-3 py-2 rounded-pill';
            licBadge.innerHTML = '<i class="bi bi-shield-check me-1"></i> License Valid';
        } else {
            licBadge.className = 'badge bg-danger-subtle text-danger border border-danger px-3 py-2 rounded-pill';
            licBadge.innerHTML = `<i class="bi bi-shield-exclamation me-1"></i> ${data.license_message}`;
        }

        // 3. Mode Badge & Tab Header
        const mode = data.config ? (data.config.trading_mode || 'paper') : 'paper';
        const isBybit = (mode === 'live_bybit');
        const isLiveMode = (mode === 'live_indodax');
        const modeBadge = document.getElementById('trading-mode-badge');
        const tabTitle = document.getElementById('positions-tab-title');
        const thProfit = document.getElementById('th-profit-label');

        if (modeBadge) {
            if (isBybit) {
                modeBadge.className = 'badge bg-warning text-dark border border-warning';
                modeBadge.innerHTML = '<span class="spinner-grow spinner-grow-sm me-1 text-dark"></span> ⚡ Live Bybit Futures (5x)';
            } else if (isLiveMode) {
                modeBadge.className = 'badge bg-danger-subtle text-rose border border-danger';
                modeBadge.innerHTML = '<span class="spinner-grow spinner-grow-sm me-1 text-danger"></span> Live Indodax (Real)';
            } else {
                modeBadge.className = 'badge bg-success-subtle text-emerald border border-success';
                modeBadge.innerHTML = '<i class="bi bi-shield-check me-1"></i> Paper Trading Mode';
            }
        }

        if (tabTitle) {
            if (isBybit) {
                tabTitle.innerHTML = '<span class="text-warning fw-bold"><i class="bi bi-lightning-charge me-1"></i>Posisi Bybit Futures (Real 2-Arah)</span>';
            } else if (isLiveMode) {
                tabTitle.innerHTML = '<span class="text-danger fw-bold"><i class="bi bi-broadcast me-1"></i>Posisi Trading Indodax (Real)</span>';
            } else {
                tabTitle.innerText = 'Posisi Paper Trading';
            }
        }

        const btnSync = document.getElementById('btn-sync-wallet');
        if (btnSync) {
            if (isBybit) {
                btnSync.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i> Sinkronkan Posisi Bybit';
                btnSync.title = 'Sinkronkan posisi aktif dari akun Bybit Futures V5';
            } else if (isLiveMode) {
                btnSync.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i> Sinkronkan Aset Indodax';
                btnSync.title = 'Sinkronkan koin yang ada di dompet Indodax ke tabel posisi bot';
            } else {
                btnSync.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i> Sinkronkan Posisi';
            }
        }

        if (thProfit) {
            thProfit.innerText = isLiveMode ? 'Profit (IDR)' : 'Profit ($ USDT)';
        }

        // 3b. Exchange Real Account Status
        const indodaxStatusElem = document.getElementById('indodax-acc-status');
        const indodaxBalElem = document.getElementById('indodax-idr-bal');
        
        if (isBybit) {
            if (data.bybit_account && data.bybit_account.status === 'success') {
                const bAcc = data.bybit_account;
                if (indodaxStatusElem) indodaxStatusElem.innerHTML = `<span class="text-emerald"><i class="bi bi-check-circle-fill me-1"></i>Bybit V5 Terhubung</span>`;
                if (indodaxBalElem) indodaxBalElem.innerText = `Tersedia: $${Number(bAcc.total_available_balance || 0).toFixed(2)} USDT`;
            } else {
                if (indodaxStatusElem) indodaxStatusElem.innerHTML = `<span class="text-warning"><i class="bi bi-exclamation-circle me-1"></i>Bybit Belum Terhubung</span>`;
                if (indodaxBalElem) indodaxBalElem.innerText = '';
            }
        } else if (data.indodax_account && data.indodax_account.status === 'success') {
            const acc = data.indodax_account;
            if (indodaxStatusElem) indodaxStatusElem.innerHTML = `<span class="text-emerald"><i class="bi bi-check-circle-fill me-1"></i>Terhubung (UID: ${acc.uid})</span>`;
            if (indodaxBalElem) indodaxBalElem.innerText = `Saldo: Rp ${Number(acc.idr_balance || 0).toLocaleString('id-ID')}`;
        } else {
            if (indodaxStatusElem) indodaxStatusElem.innerHTML = `<span class="text-secondary"><i class="bi bi-exclamation-circle me-1"></i>Belum Terhubung</span>`;
            if (indodaxBalElem) indodaxBalElem.innerText = '';
        }

        // 3c. Account Balance & Floating PnL Display
        const positions = (data.account && data.account.positions) ? data.account.positions : [];
        if (isBybit && data.bybit_account && data.bybit_account.status === 'success') {
            const bAcc = data.bybit_account;
            const bal = Number(bAcc.total_wallet_balance || 0);
            const upl = Number(bAcc.total_perp_upl || 0);
            const eq = Number(bAcc.total_equity || bal);

            document.getElementById('acc-balance').innerHTML = `$${bal.toFixed(2)} <span class="fs-6 text-muted font-normal">USDT</span>`;
            document.getElementById('acc-balance-idr').innerText = `Rp ${(bal * 15500).toLocaleString('id-ID')} (Bybit Unified)`;

            const pnlElem = document.getElementById('acc-floating');
            if (upl > 0) {
                pnlElem.className = 'kpi-value pnl-pos';
                pnlElem.innerText = `+$${upl.toFixed(2)}`;
            } else if (upl < 0) {
                pnlElem.className = 'kpi-value pnl-neg';
                pnlElem.innerText = `-$${Math.abs(upl).toFixed(2)}`;
            } else {
                pnlElem.className = 'kpi-value text-secondary';
                pnlElem.innerText = `$0.00`;
            }
            document.getElementById('acc-equity').innerText = `Equity: $${eq.toFixed(2)}`;

            renderPositions(positions);
        } else if (isLiveMode && data.indodax_account && data.indodax_account.status === 'success') {
            const indodaxBal = Number(data.indodax_account.idr_balance) || 0;
            const livePositions = positions.filter(p => p.mode === 'live_indodax' || p.currency === 'IDR');
            const totalIdrPnl = livePositions.reduce((sum, p) => sum + (Number(p.profit) || 0), 0);
            
            document.getElementById('acc-balance').innerHTML = `Rp ${indodaxBal.toLocaleString('id-ID')} <span class="fs-6 text-muted font-normal">IDR</span>`;
            document.getElementById('acc-balance-idr').innerText = `Indodax Real (UID: ${data.indodax_account.uid})`;
            
            const pnlElem = document.getElementById('acc-floating');
            if (totalIdrPnl > 0) {
                pnlElem.className = 'kpi-value pnl-pos';
                pnlElem.innerText = `+Rp ${Math.round(totalIdrPnl).toLocaleString('id-ID')}`;
            } else if (totalIdrPnl < 0) {
                pnlElem.className = 'kpi-value pnl-neg';
                pnlElem.innerText = `-Rp ${Math.abs(Math.round(totalIdrPnl)).toLocaleString('id-ID')}`;
            } else {
                pnlElem.className = 'kpi-value text-secondary';
                pnlElem.innerText = `Rp 0`;
            }
            document.getElementById('acc-equity').innerText = `Est. Saldo + PnL: Rp ${(indodaxBal + totalIdrPnl).toLocaleString('id-ID')}`;

            // Render Positions Table
            renderPositions(positions);
        } else if (data.account) {
            const bal = data.account.balance || 0;
            const balIdr = data.account.balance_idr || 0;
            const floatPnl = Number(data.account.floating_profit) || 0;
            const equity = data.account.equity || bal;

            document.getElementById('acc-balance').innerHTML = `$${bal.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})} <span class="fs-6 text-muted font-normal">USDT</span>`;
            document.getElementById('acc-balance-idr').innerText = `Rp ${balIdr.toLocaleString('id-ID')} IDR`;
            
            const pnlElem = document.getElementById('acc-floating');
            if (floatPnl > 0) {
                pnlElem.className = 'kpi-value pnl-pos';
                pnlElem.innerText = `+$${floatPnl.toFixed(2)}`;
            } else if (floatPnl < 0) {
                pnlElem.className = 'kpi-value pnl-neg';
                pnlElem.innerText = `-$${Math.abs(floatPnl).toFixed(2)}`;
            } else {
                pnlElem.className = 'kpi-value text-secondary';
                pnlElem.innerText = `$0.00`;
            }
            document.getElementById('acc-equity').innerText = `Equity: $${equity.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

            // Render Positions Table
            renderPositions(positions);
        }


        // 4. Render Active Coin Pills
        if (data.config && data.config.symbols) {
            renderCoinPills(data.config.symbols);
        }

        // 5. GainzAlgo V2 Signal HUD for Selected Coin
        if (data.gainzalgo_v2 && data.gainzalgo_v2.signal) {
            const g = data.gainzalgo_v2;
            const sigElem = document.getElementById('hud-signal');
            sigElem.innerText = g.signal;
            if (g.signal === 'BUY') {
                sigElem.className = 'hud-signal-pill text-emerald';
            } else if (g.signal === 'SELL') {
                sigElem.className = 'hud-signal-pill text-rose';
            } else {
                sigElem.className = 'hud-signal-pill text-warning';
            }

            document.getElementById('hud-symbol-tf').innerText = `${selectedSymbol} (${g.timeframe || '5m'})`;
            document.getElementById('hud-trend-power').innerText = g.trend_power || '--';
            document.getElementById('hud-entry').innerText = g.entry_price ? `$${g.entry_price}` : '--';
            document.getElementById('hud-tp').innerText = g.tp_price ? `$${g.tp_price}` : '--';
            document.getElementById('hud-sl').innerText = g.sl_price ? `$${g.sl_price}` : '--';
            document.getElementById('hud-rr').innerText = g.rr_ratio || '1:2.0';
            document.getElementById('hud-atr').innerText = g.atr || '--';
            document.getElementById('hud-rsi').innerText = g.rsi || '--';
            document.getElementById('hud-confidence').innerText = `${g.confidence || 50}%`;
        }

        // 6. Config Values
        if (data.config) {
            const cfg = data.config;
            if (document.getElementById('cfg-bybit-key') && !document.getElementById('cfg-bybit-key').value) {
                document.getElementById('cfg-bybit-key').value = cfg.bybit_api_key || '';
            }
            if (document.getElementById('cfg-bybit-secret') && !document.getElementById('cfg-bybit-secret').value) {
                document.getElementById('cfg-bybit-secret').value = cfg.bybit_api_secret || '';
            }
            if (document.getElementById('cfg-bybit-leverage') && !document.getElementById('cfg-bybit-leverage').getAttribute('data-loaded')) {
                document.getElementById('cfg-bybit-leverage').value = cfg.bybit_leverage || 5;
                document.getElementById('cfg-bybit-leverage').setAttribute('data-loaded', 'true');
            }
            if (document.getElementById('cfg-trade-margin-usdt') && !document.getElementById('cfg-trade-margin-usdt').getAttribute('data-loaded')) {
                document.getElementById('cfg-trade-margin-usdt').value = cfg.trade_margin_usdt || 2.0;
                document.getElementById('cfg-trade-margin-usdt').setAttribute('data-loaded', 'true');
            }
            if (document.getElementById('cfg-indodax-key') && !document.getElementById('cfg-indodax-key').value) {
                document.getElementById('cfg-indodax-key').value = cfg.indodax_api_key || '';
            }
            if (document.getElementById('cfg-indodax-secret') && !document.getElementById('cfg-indodax-secret').value) {
                document.getElementById('cfg-indodax-secret').value = cfg.indodax_secret_key || '';
            }
            if (document.getElementById('cfg-trading-mode') && !document.getElementById('cfg-trading-mode').getAttribute('data-loaded')) {
                document.getElementById('cfg-trading-mode').value = cfg.trading_mode || 'paper';
                document.getElementById('cfg-trading-mode').setAttribute('data-loaded', 'true');
            }
            if (document.getElementById('cfg-groq-key') && !document.getElementById('cfg-groq-key').value) {
                document.getElementById('cfg-groq-key').value = cfg.groq_api_key || '';
            }
            if (document.getElementById('cfg-timeframe') && !document.getElementById('cfg-timeframe').getAttribute('data-loaded')) {
                document.getElementById('cfg-timeframe').value = cfg.timeframe || '5m';
                document.getElementById('cfg-timeframe').setAttribute('data-loaded', 'true');
            }
            if (document.getElementById('cfg-symbols') && !document.getElementById('cfg-symbols').getAttribute('data-loaded')) {
                document.getElementById('cfg-symbols').value = (cfg.symbols || ['BTCUSDT']).join(', ');
                document.getElementById('cfg-symbols').setAttribute('data-loaded', 'true');
            }
            if (document.getElementById('cfg-max-positions') && !document.getElementById('cfg-max-positions').getAttribute('data-loaded')) {
                document.getElementById('cfg-max-positions').value = cfg.max_open_positions || 2;
                document.getElementById('cfg-max-positions').setAttribute('data-loaded', 'true');
            }
            if (document.getElementById('cfg-interval') && !document.getElementById('cfg-interval').getAttribute('data-loaded')) {
                document.getElementById('cfg-interval').value = cfg.loop_interval_seconds || 15;
                document.getElementById('cfg-interval').setAttribute('data-loaded', 'true');
            }
        }

        // 7. Update AI Card Symbol & Button Label
        const aiCardSym = document.getElementById('ai-card-symbol');
        if (aiCardSym) aiCardSym.innerText = selectedSymbol;
        const aiBtnLbl = document.getElementById('ai-btn-label');
        if (aiBtnLbl) aiBtnLbl.innerText = `Analisis ${selectedSymbol} Sekarang`;

        // 8. Latest AI Analysis Result for Selected Coin
        if (data.latest_ai && data.latest_ai.recommendation && (!data.latest_ai.symbol || data.latest_ai.symbol === selectedSymbol)) {
            renderAiAnalysisResult(data.latest_ai);
        } else {
            // Not yet analyzed for this specific coin
            renderAiPlaceholder(selectedSymbol);
        }

        // 8. System Logs
        if (data.logs) {
            const logBox = document.getElementById('log-terminal');
            const shouldScroll = logBox.scrollTop + logBox.clientHeight >= logBox.scrollHeight - 20;
            logBox.innerText = data.logs.join('\n');
            if (shouldScroll) {
                logBox.scrollTop = logBox.scrollHeight;
            }
        }

    } catch (err) {
        console.error('Error fetching status:', err);
    }
}

let currentActiveTab = 'positions';
let cachedTradeHistory = [];
let historyFilter = 'ALL';

function switchTab(tabName) {
    currentActiveTab = tabName;
    ['positions', 'history', 'logs', 'config'].forEach(t => {
        const btn = document.getElementById(`${t}-tab`);
        const pane = document.getElementById(`${t}-pane`);
        if (btn && pane) {
            if (t === tabName) {
                btn.classList.add('active');
                pane.classList.add('show', 'active');
                pane.style.display = 'block';
            } else {
                btn.classList.remove('active');
                pane.classList.remove('show', 'active');
                pane.style.display = 'none';
            }
        }
    });

    if (tabName === 'history') {
        fetchTradeHistory();
    }
}

async function fetchTradeHistory(force = false) {
    const tbody = document.getElementById('history-tbody');
    if (!tbody) return;
    if (force || cachedTradeHistory.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4"><span class="spinner-border spinner-border-sm me-2 text-info"></span>Memuat riwayat transaksi perdagangan...</td></tr>';
    }

    try {
        const res = await fetch('/api/trades/history');
        const data = await res.json();
        if (data.status === 'success') {
            cachedTradeHistory = data.history || [];
            renderTradeHistorySummary(data.summary || {});
            renderTradeHistory(cachedTradeHistory);
        } else {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-4">${data.message || 'Gagal memuat riwayat'}</td></tr>`;
        }
    } catch (err) {
        console.error('Error fetching trade history:', err);
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-4">Error koneksi riwayat: ${err}</td></tr>`;
    }
}

function renderTradeHistorySummary(s) {
    const elTotal = document.getElementById('hist-total-trades');
    const elBuy = document.getElementById('hist-buy-vol');
    const elSell = document.getElementById('hist-sell-vol');
    const elPnl = document.getElementById('hist-realized-pnl');

    const isUSDT = (s.mode === 'live_bybit' || s.currency === 'USDT');

    if (elTotal) elTotal.innerText = `${s.total_trades || 0} Posisi`;
    
    if (isUSDT) {
        const totalVol = Number(s.total_volume_usdt || s.total_buy_volume_usdt || 0);
        if (elBuy) elBuy.innerText = `$${totalVol.toFixed(2)} USDT`;
        if (elSell) elSell.innerText = `Bybit Futures 5x`;
        if (elPnl) {
            const pnl = Number(s.total_realized_profit_usdt !== undefined ? s.total_realized_profit_usdt : s.total_realized_profit) || 0;
            if (pnl > 0) {
                elPnl.className = 'fw-bold fs-6 text-emerald';
                elPnl.innerText = `+$${pnl.toFixed(4)} USDT`;
            } else if (pnl < 0) {
                elPnl.className = 'fw-bold fs-6 text-rose';
                elPnl.innerText = `-$${Math.abs(pnl).toFixed(4)} USDT`;
            } else {
                elPnl.className = 'fw-bold fs-6 text-secondary';
                elPnl.innerText = `$0.00 USDT`;
            }
        }
    } else {
        if (elBuy) elBuy.innerText = `Rp ${Number(s.total_buy_volume_idr || 0).toLocaleString('id-ID')}`;
        if (elSell) elSell.innerText = `Rp ${Number(s.total_sell_volume_idr || 0).toLocaleString('id-ID')}`;
        if (elPnl) {
            const pnl = Number(s.total_realized_profit_idr !== undefined ? s.total_realized_profit_idr : s.total_realized_profit) || 0;
            if (pnl > 0) {
                elPnl.className = 'fw-bold fs-6 text-emerald';
                elPnl.innerText = `+Rp ${Math.round(pnl).toLocaleString('id-ID')}`;
            } else if (pnl < 0) {
                elPnl.className = 'fw-bold fs-6 text-rose';
                elPnl.innerText = `-Rp ${Math.abs(Math.round(pnl)).toLocaleString('id-ID')}`;
            } else {
                elPnl.className = 'fw-bold fs-6 text-secondary';
                elPnl.innerText = `Rp 0`;
            }
        }
    }
}

function applyHistoryFilter(filterVal) {
    historyFilter = filterVal;
    renderTradeHistory(cachedTradeHistory);
}

function renderTradeHistory(trades) {
    const tbody = document.getElementById('history-tbody');
    if (!tbody) return;

    let filtered = trades;
    if (historyFilter !== 'ALL') {
        filtered = trades.filter(t => t.side === historyFilter);
    }

    if (!filtered || filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">Belum ada riwayat transaksi pada filter ini.</td></tr>';
        return;
    }

    let html = '';
    filtered.forEach(t => {
        const isUSDT = (t.mode === 'live_bybit' || t.currency === 'USDT');
        const isBuy = t.side === 'BUY';
        let sideBadge = '';
        if (isUSDT) {
            sideBadge = isBuy
                ? '<span class="badge bg-success-subtle text-emerald border border-success px-2 py-1"><i class="bi bi-arrow-up-right me-1"></i>BUY / LONG</span>'
                : '<span class="badge bg-danger-subtle text-rose border border-danger px-2 py-1"><i class="bi bi-arrow-down-right me-1"></i>SELL / SHORT</span>';
        } else {
            sideBadge = isBuy
                ? '<span class="badge bg-success-subtle text-emerald border border-success px-2 py-1"><i class="bi bi-arrow-down-left me-1"></i>BUY</span>'
                : '<span class="badge bg-danger-subtle text-rose border border-danger px-2 py-1"><i class="bi bi-arrow-up-right me-1"></i>SELL</span>';
        }

        const pnlVal = Number(t.pnl) || 0;
        let pnlText = '-';
        let pnlClass = 'text-muted';
        
        if (pnlVal > 0) {
            pnlText = isUSDT ? `+$${pnlVal.toFixed(4)}` : `+Rp ${Math.round(pnlVal).toLocaleString('id-ID')}`;
            pnlClass = 'text-emerald fw-bold';
        } else if (pnlVal < 0) {
            pnlText = isUSDT ? `-$${Math.abs(pnlVal).toFixed(4)}` : `-Rp ${Math.abs(Math.round(pnlVal)).toLocaleString('id-ID')}`;
            pnlClass = 'text-rose fw-bold';
        } else {
            pnlText = isUSDT ? '$0.00' : 'Rp 0';
            pnlClass = 'text-secondary';
        }

        let priceFmt = '';
        if (isUSDT) {
            if (t.price_entry && t.price_entry > 0) {
                priceFmt = `<span class="text-secondary small">$${t.price_entry}</span> <i class="bi bi-arrow-right text-warning mx-1" style="font-size:0.68rem;"></i> <strong class="text-light">$${t.price}</strong>`;
            } else {
                priceFmt = `$${Number(t.price).toFixed(t.price < 1 ? 4 : 2)}`;
            }
        } else {
            priceFmt = `Rp ${Number(t.price).toLocaleString('id-ID')}`;
        }

        const totalFmt = isUSDT
            ? `$${Number(t.quote_qty || 0).toFixed(2)}`
            : `Rp ${Number(t.quote_qty || (t.price * t.qty)).toLocaleString('id-ID')}`;

        const qtyVal = Number(t.amount !== undefined ? t.amount : t.qty) || 0;
        const qtyFmt = qtyVal < 1 ? qtyVal.toFixed(4) : qtyVal.toFixed(2);

        html += `
            <tr>
                <td class="font-mono text-muted small">${t.datetime || '--'}</td>
                <td class="font-mono text-light fw-semibold small">#${String(t.order_id || '').substring(0, 10)}...</td>
                <td>
                    <span class="fw-bold text-light">${t.symbol}</span>
                </td>
                <td>${sideBadge}</td>
                <td class="font-mono">${qtyFmt}</td>
                <td class="font-mono">${priceFmt}</td>
                <td class="font-mono fw-semibold">${totalFmt}</td>
                <td class="font-mono"><span class="${pnlClass}">${pnlText}</span></td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}


function renderPositions(positions) {
    const tbody = document.getElementById('positions-tbody');
    if (!tbody) return;
    if (!positions || positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">Belum ada posisi terbuka saat ini.</td></tr>';
        return;
    }

    let html = '';
    positions.forEach(p => {
        const isBybit = (p.mode === 'live_bybit');
        const isIndodax = (p.mode === 'live_indodax') || (p.currency === 'IDR');
        const profit = Number(p.profit) || 0;
        let pnlText = '$0.00';
        let pnlClass = 'pnl-zero';

        if (isIndodax) {
            if (profit > 0) {
                pnlText = `+Rp ${Math.round(profit).toLocaleString('id-ID')}`;
                pnlClass = 'pnl-pos';
            } else if (profit < 0) {
                pnlText = `-Rp ${Math.abs(Math.round(profit)).toLocaleString('id-ID')}`;
                pnlClass = 'pnl-neg';
            } else {
                pnlText = `Rp 0`;
            }
        } else {
            if (profit > 0) {
                pnlText = `+$${profit.toFixed(4)}`;
                pnlClass = 'pnl-pos';
            } else if (profit < 0) {
                pnlText = `-$${Math.abs(profit).toFixed(4)}`;
                pnlClass = 'pnl-neg';
            }
        }

        let sideBadge = '';
        if (isBybit) {
            sideBadge = (p.type === 'BUY') 
                ? `<span class="badge bg-success text-light border border-success"><i class="bi bi-arrow-up-right me-1"></i>LONG ${p.leverage || 5}x</span>`
                : `<span class="badge bg-danger text-light border border-danger"><i class="bi bi-arrow-down-right me-1"></i>SHORT ${p.leverage || 5}x</span>`;
        } else if (isIndodax) {
            sideBadge = (p.type === 'BUY') 
                ? '<span class="badge bg-danger text-light border border-danger"><i class="bi bi-broadcast me-1"></i>REAL BUY</span>'
                : '<span class="badge bg-warning text-dark border border-warning"><i class="bi bi-broadcast me-1"></i>REAL SELL</span>';
        } else {
            sideBadge = (p.type === 'BUY') 
                ? '<span class="badge bg-success-subtle text-success border border-success">BUY</span>'
                : '<span class="badge bg-danger-subtle text-danger border border-danger">SELL</span>';
        }

        const priceOpenFmt = isIndodax ? `Rp ${Number(p.price_open).toLocaleString('id-ID')}` : `$${p.price_open}`;
        const slFmt = isIndodax ? (p.sl ? `Rp ${Number(p.sl).toLocaleString('id-ID')}` : '--') : (p.sl ? `$${p.sl}` : '--');
        const tpFmt = isIndodax ? (p.tp ? `Rp ${Number(p.tp).toLocaleString('id-ID')}` : '--') : (p.tp ? `$${p.tp}` : '--');

        html += `
            <tr>
                <td class="font-mono text-muted">#${p.ticket}</td>
                <td>
                    <a href="javascript:void(0)" onclick="selectCoin('${p.symbol}')" class="text-light text-decoration-none fw-bold hover-cyan" title="Klik untuk ganti Analisis & Chart ke koin ini">
                        ${p.symbol} <i class="bi bi-box-arrow-up-right text-info ms-1" style="font-size:0.7rem;"></i>
                    </a>
                </td>
                <td>${sideBadge}</td>
                <td class="font-mono fw-semibold">${p.amount}</td>
                <td class="font-mono">${priceOpenFmt}</td>
                <td class="font-mono text-danger">${slFmt}</td>
                <td class="font-mono text-success">${tpFmt}</td>
                <td class="font-mono fw-bold"><span class="${pnlClass}">${pnlText}</span></td>
                <td class="text-center">
                    <button class="btn btn-sm btn-outline-danger px-2 py-0 rounded-pill" style="font-size: 0.7rem;" onclick="closePosition('${p.ticket}')">
                        <i class="bi bi-x me-1"></i>Tutup
                    </button>
                </td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

async function closePosition(ticket) {
    try {
        const res = await fetch('/api/positions/close', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticket: ticket })
        });
        const data = await res.json();
        fetchStatus();
    } catch (err) {
        alert('Gagal menutup posisi: ' + err);
    }
}

async function syncWallet() {
    const btn = document.getElementById('btn-sync-wallet');
    const isBybit = (currentTradingMode === 'live_bybit');
    const isLiveIndodax = (currentTradingMode === 'live_indodax');
    const defaultLabel = isBybit ? 'Sinkronkan Posisi Bybit' : (isLiveIndodax ? 'Sinkronkan Aset Indodax' : 'Sinkronkan Posisi');

    if (btn) btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Menyinkronkan...';
    try {
        const endpoint = isBybit ? '/api/bybit/sync-wallet' : '/api/indodax/sync-wallet';
        const res = await fetch(endpoint, { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            await fetchStatus();
        } else {
            alert('Gagal menyinkronkan: ' + (data.message || JSON.stringify(data)));
        }
    } catch (err) {
        alert('Error sinkronisasi: ' + err);
    } finally {
        if (btn) btn.innerHTML = `<i class="bi bi-arrow-repeat me-1"></i> ${defaultLabel}`;
    }
}

async function closeAllPositions() {
    const isBybit = (currentTradingMode === 'live_bybit');
    const tabTitle = document.getElementById('positions-tab-title');
    const isLive = tabTitle && tabTitle.innerText.includes('Indodax');
    const msg = isBybit
        ? 'PERINGATAN: Apakah Anda yakin ingin MENUTUP SEMUA posisi aktif Bybit Futures di harga pasar saat ini?'
        : (isLive 
            ? 'PERINGATAN: Apakah Anda yakin ingin MENJUAL dan menutup SEMUA posisi aset Indodax di harga pasar sekarang?' 
            : 'Tutup SEMUA posisi paper trading sekarang?');
    if (!confirm(msg)) return;
    try {
        const res = await fetch('/api/positions/close-all', { method: 'POST' });
        const data = await res.json();
        await fetchStatus();
    } catch (err) {
        alert('Gagal menutup semua posisi: ' + err);
    }
}

async function startBot() {
    try {
        const res = await fetch('/api/start', { method: 'POST' });
        const data = await res.json();
        fetchStatus();
    } catch (err) {
        alert('Gagal menjalankan bot: ' + err);
    }
}

async function stopBot() {
    try {
        const res = await fetch('/api/stop', { method: 'POST' });
        const data = await res.json();
        fetchStatus();
    } catch (err) {
        alert('Gagal menghentikan bot: ' + err);
    }
}

async function saveConfig(e) {
    e.preventDefault();
    const bybitKey = document.getElementById('cfg-bybit-key') ? document.getElementById('cfg-bybit-key').value.trim() : '';
    const bybitSecret = document.getElementById('cfg-bybit-secret') ? document.getElementById('cfg-bybit-secret').value.trim() : '';
    const bybitLeverage = parseInt(document.getElementById('cfg-bybit-leverage') ? document.getElementById('cfg-bybit-leverage').value : 5) || 5;
    const tradeMargin = parseFloat(document.getElementById('cfg-trade-margin-usdt') ? document.getElementById('cfg-trade-margin-usdt').value : 2.0) || 2.0;

    const indodaxKey = document.getElementById('cfg-indodax-key') ? document.getElementById('cfg-indodax-key').value.trim() : '';
    const indodaxSecret = document.getElementById('cfg-indodax-secret') ? document.getElementById('cfg-indodax-secret').value.trim() : '';
    const tradingMode = document.getElementById('cfg-trading-mode') ? document.getElementById('cfg-trading-mode').value : 'paper';
    const groqKey = document.getElementById('cfg-groq-key').value;
    const timeframe = document.getElementById('cfg-timeframe').value;
    const symbolsRaw = document.getElementById('cfg-symbols').value;
    const maxPositions = parseInt(document.getElementById('cfg-max-positions').value) || 2;
    const interval = parseInt(document.getElementById('cfg-interval').value) || 15;

    const symbols = symbolsRaw.split(',').map(s => s.trim().toUpperCase()).filter(s => s.length > 0);

    const payload = {
        bybit_api_key: bybitKey,
        bybit_api_secret: bybitSecret,
        bybit_leverage: bybitLeverage,
        trade_margin_usdt: tradeMargin,
        indodax_api_key: indodaxKey,
        indodax_secret_key: indodaxSecret,
        trading_mode: tradingMode,
        groq_api_key: groqKey,
        timeframe: timeframe,
        symbols: symbols,
        max_open_positions: maxPositions,
        loop_interval_seconds: interval
    };

    try {
        const res = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        alert(data.message);
        renderedSymbols = ''; // force re-render coin pills
        fetchStatus();
    } catch (err) {
        alert('Gagal menyimpan konfigurasi: ' + err);
    }
}

async function testBybitConnection() {
    const key = document.getElementById('cfg-bybit-key') ? document.getElementById('cfg-bybit-key').value.trim() : '';
    const secret = document.getElementById('cfg-bybit-secret') ? document.getElementById('cfg-bybit-secret').value.trim() : '';
    const alertBox = document.getElementById('bybit-test-alert');
    const msgBox = document.getElementById('bybit-test-msg');

    if (alertBox) alertBox.classList.remove('d-none');
    if (msgBox) msgBox.innerHTML = '<span class="spinner-border spinner-border-sm text-warning me-1"></span> Menguji koneksi ke Bybit V5 API...';

    try {
        const res = await fetch('/api/bybit/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: key, secret_key: secret })
        });
        const data = await res.json();
        if (data.status === 'success') {
            alertBox.className = 'alert alert-success border-success p-2 mb-3 small';
            msgBox.innerHTML = `
                <div class="fw-bold text-success mb-1"><i class="bi bi-check-circle-fill me-1"></i>Koneksi Bybit V5 Berhasil!</div>
                <div>Total Ekuitas: <strong class="text-emerald">$${Number(data.total_equity || 0).toFixed(2)} USDT</strong> | Saldo Wallet: <strong>$${Number(data.total_wallet_balance || 0).toFixed(2)} USDT</strong></div>
                <div class="mt-1 text-light">Saldo Tersedia: <strong class="text-warning">$${Number(data.total_available_balance || 0).toFixed(2)} USDT</strong> | Floating PnL: $${Number(data.total_perp_upl || 0).toFixed(2)}</div>
            `;
            fetchStatus();
        } else {
            alertBox.className = 'alert alert-danger border-danger p-2 mb-3 small';
            msgBox.innerHTML = `<div class="fw-bold text-danger mb-1"><i class="bi bi-x-circle-fill me-1"></i>Gagal Terhubung ke Bybit</div><div>${data.message || JSON.stringify(data)}</div>`;
        }
    } catch (err) {
        if (alertBox) alertBox.className = 'alert alert-danger border-danger p-2 mb-3 small';
        if (msgBox) msgBox.innerHTML = `<strong>Error Request:</strong> ${err}`;
    }
}

async function testIndodaxConnection() {
    const key = document.getElementById('cfg-indodax-key') ? document.getElementById('cfg-indodax-key').value.trim() : '';
    const secret = document.getElementById('cfg-indodax-secret') ? document.getElementById('cfg-indodax-secret').value.trim() : '';
    const alertBox = document.getElementById('indodax-test-alert');
    const msgBox = document.getElementById('indodax-test-msg');

    if (alertBox) alertBox.classList.remove('d-none');
    if (msgBox) msgBox.innerHTML = '<span class="spinner-border spinner-border-sm text-warning me-1"></span> Menguji koneksi ke Indodax Trade API 2.0...';

    try {
        const res = await fetch('/api/indodax/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: key, secret_key: secret })
        });
        const data = await res.json();
        if (data.status === 'success') {
            const nonZero = (data.balances || []).map(b => `<strong>${b.asset}</strong>: ${b.free}`).join(', ');
            alertBox.className = 'alert alert-success border-success p-2 mb-3 small';
            msgBox.innerHTML = `
                <div class="fw-bold text-success mb-1"><i class="bi bi-check-circle-fill me-1"></i>Koneksi Indodax Berhasil!</div>
                <div>UID: <strong>${data.uid}</strong> | Tipe: ${data.accountType} | Spot Trading: <strong>${data.canTrade ? 'Aktif' : 'Non-Aktif'}</strong></div>
                <div class="mt-1 text-light">Saldo IDR: <strong class="text-emerald">Rp ${Number(data.idr_balance || 0).toLocaleString('id-ID')}</strong></div>
                <div class="text-muted mt-1" style="font-size: 0.72rem;">Aset Kripto Terdeteksi: ${nonZero || 'Tidak ada koin lain'}</div>
            `;
            fetchStatus();
        } else {
            alertBox.className = 'alert alert-danger border-danger p-2 mb-3 small';
            msgBox.innerHTML = `<div class="fw-bold text-danger mb-1"><i class="bi bi-x-circle-fill me-1"></i>Gagal Terhubung ke Indodax</div><div>${data.message || JSON.stringify(data)}</div>`;
        }
    } catch (err) {
        if (alertBox) alertBox.className = 'alert alert-danger border-danger p-2 mb-3 small';
        if (msgBox) msgBox.innerHTML = `<strong>Error Request:</strong> ${err}`;
    }
}

async function runAiAnalysis() {
    document.getElementById('ai-loading').classList.remove('d-none');
    document.getElementById('ai-result-content').classList.add('d-none');

    const symbol = selectedSymbol;
    const timeframe = document.getElementById('cfg-timeframe') ? document.getElementById('cfg-timeframe').value : '5m';

    try {
        const res = await fetch('/api/ai-analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: symbol, timeframe: timeframe })
        });
        const data = await res.json();

        document.getElementById('ai-loading').classList.add('d-none');
        document.getElementById('ai-result-content').classList.remove('d-none');

        if (data.status === 'success') {
            renderAiAnalysisResult(data);
        } else {
            alert('AI Analysis Error: ' + (data.message || 'Unknown error'));
        }
    } catch (err) {
        document.getElementById('ai-loading').classList.add('d-none');
        document.getElementById('ai-result-content').classList.remove('d-none');
        alert('Gagal menjalankan AI Analysis: ' + err);
    }
}

function renderAiAnalysisResult(data) {
    const recElem = document.getElementById('ai-rec');
    recElem.innerText = data.recommendation || 'HOLD';
    if (data.recommendation === 'BUY') {
        recElem.className = 'fw-bold text-emerald mb-0';
    } else if (data.recommendation === 'SELL') {
        recElem.className = 'fw-bold text-rose mb-0';
    } else {
        recElem.className = 'fw-bold text-warning mb-0';
    }

    const confVal = data.confidence || 50;
    document.getElementById('ai-conf').innerText = `${confVal}%`;
    const barElem = document.getElementById('ai-conf-bar');
    if (barElem) {
        barElem.style.width = `${confVal}%`;
    }

    document.getElementById('ai-sup').innerText = data.support ? `$${data.support}` : '--';
    document.getElementById('ai-res').innerText = data.resistance ? `$${data.resistance}` : '--';
    document.getElementById('ai-analysis-text').innerHTML = data.analysis || 'Analisis Crypto Selesai.';
}

function renderAiPlaceholder(symbol) {
    document.getElementById('ai-rec').innerText = 'Belum Dianalisis';
    document.getElementById('ai-rec').className = 'fw-bold text-secondary mb-0';
    document.getElementById('ai-conf').innerText = '--%';
    const barElem = document.getElementById('ai-conf-bar');
    if (barElem) {
        barElem.style.width = '0%';
    }
    document.getElementById('ai-sup').innerText = '$--';
    document.getElementById('ai-res').innerText = '$--';
    document.getElementById('ai-analysis-text').innerHTML = `
        <div class="py-2 text-center text-secondary">
            Belum ada hasil analisis Groq AI untuk koin <strong>${symbol}</strong>.<br>
            Klik tombol <strong>Analisis Sekarang</strong> di atas untuk menjalankan analisis pasar koin ini.
        </div>
    `;
}
