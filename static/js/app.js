let pollTimer = null;
let selectedSymbol = 'BTCUSDT';
let renderedSymbols = '';

document.addEventListener('DOMContentLoaded', () => {
    fetchStatus();
    pollTimer = setInterval(fetchStatus, 3000);
});

function selectCoin(sym) {
    selectedSymbol = sym.toUpperCase().replace('/', '').replace('-', '');
    
    // Update active coin pill UI
    document.querySelectorAll('.coin-pill').forEach(btn => {
        if (btn.innerText.includes(selectedSymbol)) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Sync Chart Dropdown and TradingView Widget
    const chartSelect = document.getElementById('select-chart-symbol');
    if (chartSelect) {
        chartSelect.value = 'KUCOIN:' + selectedSymbol;
        if (typeof updateChartSymbol === 'function') {
            updateChartSymbol('KUCOIN:' + selectedSymbol);
        }
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

        // 3. Account Balance & Floating PnL
        if (data.account) {
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
            renderPositions(data.account.positions || []);
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

function switchTab(tabName) {
    currentActiveTab = tabName;
    ['positions', 'logs', 'config'].forEach(t => {
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
        const profit = Number(p.profit) || 0;
        let pnlText = '$0.00';
        let pnlClass = 'pnl-zero';
        if (profit > 0) {
            pnlText = `+$${profit.toFixed(2)}`;
            pnlClass = 'pnl-pos';
        } else if (profit < 0) {
            pnlText = `-$${Math.abs(profit).toFixed(2)}`;
            pnlClass = 'pnl-neg';
        }

        const sideBadge = (p.type === 'BUY') 
            ? '<span class="badge bg-success-subtle text-success border border-success">BUY</span>'
            : '<span class="badge bg-danger-subtle text-danger border border-danger">SELL</span>';

        html += `
            <tr>
                <td class="font-mono text-muted">#${p.ticket}</td>
                <td>
                    <a href="javascript:void(0)" onclick="selectCoin('${p.symbol}')" class="text-light text-decoration-none fw-bold hover-cyan" title="Klik untuk ganti Analisis & Chart ke koin ini">
                        ${p.symbol} <i class="bi bi-box-arrow-up-right text-info ms-1" style="font-size:0.7rem;"></i>
                    </a>
                </td>
                <td>${sideBadge}</td>
                <td class="font-mono">${p.amount}</td>
                <td class="font-mono">$${p.price_open}</td>
                <td class="font-mono text-danger">$${p.sl}</td>
                <td class="font-mono text-success">$${p.tp}</td>
                <td class="font-mono"><span class="${pnlClass}">${pnlText}</span></td>
                <td class="text-center">
                    <button class="btn btn-sm btn-outline-danger px-2 py-0 rounded-pill" style="font-size: 0.7rem;" onclick="closePosition(${p.ticket})">
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

async function closeAllPositions() {
    if (!confirm('Tutup SEMUA posisi paper trading sekarang?')) return;
    try {
        const res = await fetch('/api/positions/close-all', { method: 'POST' });
        const data = await res.json();
        fetchStatus();
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
    const groqKey = document.getElementById('cfg-groq-key').value;
    const timeframe = document.getElementById('cfg-timeframe').value;
    const symbolsRaw = document.getElementById('cfg-symbols').value;
    const maxPositions = parseInt(document.getElementById('cfg-max-positions').value) || 2;
    const interval = parseInt(document.getElementById('cfg-interval').value) || 15;

    const symbols = symbolsRaw.split(',').map(s => s.trim().toUpperCase()).filter(s => s.length > 0);

    const payload = {
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
