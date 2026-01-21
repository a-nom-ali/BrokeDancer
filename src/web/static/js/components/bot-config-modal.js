// src/web/static/js/components/bot-config-modal.js

class BotConfigModal {
    constructor() {
        this.modal = null;
        this.providers = [];
        this.strategies = [];
        this.editingBot = null;
    }

    async show(defaultProvider = '', defaultStrategy = '') {
        this.editingBot = null;
        await this.loadOptions();
        this.render(defaultProvider, defaultStrategy);
        this.modal.style.display = 'flex';
    }

    async showEdit(botId) {
        this.editingBot = botId;
        await this.loadOptions();
        await this.loadBotConfig(botId);
        this.modal.style.display = 'flex';
    }

    hide() {
        if (this.modal) {
            this.modal.style.display = 'none';
        }
    }

    async loadOptions() {
        try {
            // Load providers
            const providersResponse = await fetch('/api/providers');
            const providersData = await providersResponse.json();
            this.providers = Object.entries(providersData).map(([key, value]) => ({
                id: key,
                name: key,
                description: value
            }));

            // Load strategies
            const strategiesResponse = await fetch('/api/strategies');
            const strategiesData = await strategiesResponse.json();
            this.strategies = Object.entries(strategiesData).map(([key, value]) => ({
                id: key,
                name: key,
                description: value
            }));
        } catch (error) {
            console.error('Error loading options:', error);
        }
    }

    async loadBotConfig(botId) {
        try {
            const response = await fetch(`/api/bots/${botId}`);
            const bot = await response.json();
            this.renderEditForm(bot);
        } catch (error) {
            console.error('Error loading bot config:', error);
            showNotification('Failed to load bot configuration', 'error');
        }
    }

    render(defaultProvider = '', defaultStrategy = '') {
        // Remove existing modal if any
        const existing = document.getElementById('botConfigModal');
        if (existing) existing.remove();

        this.modal = document.createElement('div');
        this.modal.id = 'botConfigModal';
        this.modal.className = 'modal';
        this.modal.innerHTML = `
            <div class="modal-content modal-content--large">
                <div class="modal-header">
                    <h2>🤖 Create New Bot</h2>
                    <button class="modal-close" onclick="botConfigModal.hide()">×</button>
                </div>
                <div class="modal-body">
                    <form id="createBotForm" onsubmit="botConfigModal.createBot(event)">
                        ${this.renderFormSections(defaultProvider, defaultStrategy, {})}

                        <div class="form-actions">
                            <button type="button" class="btn btn--secondary" onclick="botConfigModal.hide()">Cancel</button>
                            <button type="submit" class="btn btn--primary">Create & Start Bot</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.body.appendChild(this.modal);

        // Close on background click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });
    }

    renderEditForm(bot) {
        // Remove existing modal if any
        const existing = document.getElementById('botConfigModal');
        if (existing) existing.remove();

        this.modal = document.createElement('div');
        this.modal.id = 'botConfigModal';
        this.modal.className = 'modal';
        this.modal.innerHTML = `
            <div class="modal-content modal-content--large">
                <div class="modal-header">
                    <h2>⚙️ Configure Bot</h2>
                    <button class="modal-close" onclick="botConfigModal.hide()">×</button>
                </div>
                <div class="modal-body">
                    <form id="editBotForm" onsubmit="botConfigModal.updateBot(event)">
                        ${this.renderFormSections(bot.provider, bot.strategy, bot.config || {}, true)}

                        <div class="form-actions">
                            <button type="button" class="btn btn--secondary" onclick="botConfigModal.hide()">Cancel</button>
                            <button type="submit" class="btn btn--primary">Save Configuration</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.body.appendChild(this.modal);

        // Close on background click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });
    }

    renderFormSections(defaultProvider, defaultStrategy, config, isEdit = false) {
        return `
            <!-- Basic Configuration -->
            <div class="config-section">
                <h3>Basic Configuration</h3>

                <div class="form-group">
                    <label>Provider *</label>
                    <select name="provider" required ${isEdit ? 'disabled' : ''}>
                        <option value="">Select Provider...</option>
                        ${this.providers.map(p => `
                            <option value="${p.id}" ${p.id === defaultProvider ? 'selected' : ''}>
                                ${p.name} - ${p.description}
                            </option>
                        `).join('')}
                    </select>
                    ${isEdit ? '<small class="text-muted">Provider cannot be changed after creation</small>' : ''}
                </div>

                <div class="form-group">
                    <label>Strategy *</label>
                    <select name="strategy" required ${isEdit ? 'disabled' : ''}>
                        <option value="">Select Strategy...</option>
                        ${this.strategies.map(s => `
                            <option value="${s.id}" ${s.id === defaultStrategy ? 'selected' : ''}>
                                ${s.name} - ${s.description}
                            </option>
                        `).join('')}
                    </select>
                    ${isEdit ? '<small class="text-muted">Strategy cannot be changed after creation</small>' : ''}
                </div>

                <div class="form-group">
                    <label>Trading Pair</label>
                    <input type="text" name="pair" placeholder="e.g., BTC/USDT" value="${config.pair || ''}">
                    <small>Leave empty to use strategy defaults</small>
                </div>
            </div>

            <!-- Risk Management -->
            <div class="config-section">
                <h3>Risk Management</h3>

                <div class="form-row">
                    <div class="form-col">
                        <label>Max Daily Loss ($)</label>
                        <input type="number" name="max_loss" placeholder="100" step="0.01" value="${config.max_daily_loss || ''}">
                    </div>
                    <div class="form-col">
                        <label>Max Trades/Day</label>
                        <input type="number" name="max_trades" placeholder="50" value="${config.max_trades_per_day || ''}">
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-col">
                        <label>Position Size ($)</label>
                        <input type="number" name="position_size" placeholder="10" step="0.01" value="${config.position_size || ''}">
                        <small>Default bet amount per trade</small>
                    </div>
                    <div class="form-col">
                        <label>Max Position Size ($)</label>
                        <input type="number" name="max_position_size" placeholder="100" step="0.01" value="${config.max_position_size || ''}">
                        <small>Maximum allowed bet</small>
                    </div>
                </div>

                <div class="form-group">
                    <label>Stop Loss (%)</label>
                    <input type="number" name="stop_loss" placeholder="5" step="0.1" value="${config.stop_loss || ''}">
                    <small>Auto-close position if loss exceeds this percentage</small>
                </div>

                <div class="form-group">
                    <label>Take Profit (%)</label>
                    <input type="number" name="take_profit" placeholder="10" step="0.1" value="${config.take_profit || ''}">
                    <small>Auto-close position if profit exceeds this percentage</small>
                </div>
            </div>

            <!-- Trading Parameters -->
            <div class="config-section">
                <h3>Trading Parameters</h3>

                <div class="form-row">
                    <div class="form-col">
                        <label>Trading Interval (minutes)</label>
                        <input type="number" name="interval" placeholder="15" value="${config.interval || 15}">
                        <small>How often to check for signals</small>
                    </div>
                    <div class="form-col">
                        <label>Cooldown Period (minutes)</label>
                        <input type="number" name="cooldown" placeholder="60" value="${config.cooldown || ''}">
                        <small>Minimum time between trades</small>
                    </div>
                </div>

                <div class="form-group">
                    <label>Price Slippage (%)</label>
                    <input type="number" name="slippage" placeholder="0.5" step="0.1" value="${config.slippage || ''}">
                    <small>Maximum acceptable price slippage</small>
                </div>

                <div class="form-group">
                    <label>
                        <input type="checkbox" name="compound_profits" ${config.compound_profits ? 'checked' : ''}>
                        Compound profits (increase position size with winnings)
                    </label>
                </div>
            </div>

            <!-- Notifications -->
            <div class="config-section">
                <h3>Notifications</h3>

                <div class="form-group">
                    <label>
                        <input type="checkbox" name="notify_on_trade" ${config.notify_on_trade !== false ? 'checked' : ''}>
                        Notify on each trade
                    </label>
                </div>

                <div class="form-group">
                    <label>
                        <input type="checkbox" name="notify_on_error" ${config.notify_on_error !== false ? 'checked' : ''}>
                        Notify on errors
                    </label>
                </div>

                <div class="form-group">
                    <label>
                        <input type="checkbox" name="notify_on_stop" ${config.notify_on_stop ? 'checked' : ''}>
                        Notify when bot stops
                    </label>
                </div>

                <div class="form-group">
                    <label>Email Notifications</label>
                    <input type="email" name="notification_email" placeholder="your@email.com" value="${config.notification_email || ''}">
                    <small>Leave empty to disable email notifications</small>
                </div>
            </div>

            <!-- Advanced Settings -->
            <div class="config-section config-section--collapsible">
                <h3 onclick="this.parentElement.classList.toggle('collapsed')">
                    Advanced Settings
                    <span class="collapse-icon">▼</span>
                </h3>
                <div class="config-section__content">
                    <div class="form-group">
                        <label>Retry Attempts</label>
                        <input type="number" name="retry_attempts" placeholder="3" value="${config.retry_attempts || 3}">
                        <small>Number of times to retry failed API calls</small>
                    </div>

                    <div class="form-group">
                        <label>Timeout (seconds)</label>
                        <input type="number" name="timeout" placeholder="30" value="${config.timeout || 30}">
                        <small>API request timeout</small>
                    </div>

                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="dry_run" ${config.dry_run ? 'checked' : ''}>
                            Dry run mode (simulate trades without real money)
                        </label>
                    </div>

                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="verbose_logging" ${config.verbose_logging ? 'checked' : ''}>
                            Verbose logging (detailed debug information)
                        </label>
                    </div>

                    <div class="form-group">
                        <label>Custom Parameters (JSON)</label>
                        <textarea name="custom_params" rows="4" placeholder='{"key": "value"}'>${config.custom_params ? JSON.stringify(config.custom_params, null, 2) : ''}</textarea>
                        <small>Additional strategy-specific parameters</small>
                    </div>
                </div>
            </div>

            ${!isEdit ? `
            <div class="form-group">
                <label>
                    <input type="checkbox" name="auto_start" checked>
                    Auto-start bot after creation
                </label>
            </div>
            ` : ''}
        `;
    }

    async createBot(event) {
        event.preventDefault();
        const formData = new FormData(event.target);

        const provider = formData.get('provider');
        const strategy = formData.get('strategy');
        const autoStart = formData.get('auto_start') === 'on';

        // Build config object
        const config = this.buildConfigFromForm(formData);

        try {
            // Create bot
            const response = await fetch('/api/bots', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider, strategy, config })
            });

            const result = await response.json();

            if (response.ok) {
                const botId = result.bot_id;
                showNotification('✅ Bot created successfully!', 'success');

                // Auto-start if checked
                if (autoStart) {
                    const startResponse = await fetch(`/api/bots/${botId}/start`, {
                        method: 'POST'
                    });

                    if (startResponse.ok) {
                        showNotification('🚀 Bot started!', 'success');
                    }
                }

                this.hide();
                // Reload dashboard to show new bot
                if (typeof loadBots === 'function') {
                    loadBots();
                }
            } else {
                showNotification(`❌ ${result.error || 'Failed to create bot'}`, 'error');
            }
        } catch (error) {
            console.error('Error creating bot:', error);
            showNotification('❌ Error creating bot', 'error');
        }
    }

    async updateBot(event) {
        event.preventDefault();
        const formData = new FormData(event.target);

        // Build config object
        const config = this.buildConfigFromForm(formData);

        try {
            const response = await fetch(`/api/bots/${this.editingBot}/config`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config })
            });

            const result = await response.json();

            if (response.ok) {
                showNotification('✅ Configuration saved successfully!', 'success');
                this.hide();
                // Reload dashboard to reflect changes
                if (typeof loadBots === 'function') {
                    loadBots();
                }
            } else {
                showNotification(`❌ ${result.error || 'Failed to update configuration'}`, 'error');
            }
        } catch (error) {
            console.error('Error updating bot config:', error);
            showNotification('❌ Error updating configuration', 'error');
        }
    }

    buildConfigFromForm(formData) {
        const config = {};

        // Basic settings
        if (formData.get('pair')) config.pair = formData.get('pair');
        if (formData.get('interval')) config.interval = parseInt(formData.get('interval'));

        // Risk management
        if (formData.get('max_loss')) config.max_daily_loss = parseFloat(formData.get('max_loss'));
        if (formData.get('max_trades')) config.max_trades_per_day = parseInt(formData.get('max_trades'));
        if (formData.get('position_size')) config.position_size = parseFloat(formData.get('position_size'));
        if (formData.get('max_position_size')) config.max_position_size = parseFloat(formData.get('max_position_size'));
        if (formData.get('stop_loss')) config.stop_loss = parseFloat(formData.get('stop_loss'));
        if (formData.get('take_profit')) config.take_profit = parseFloat(formData.get('take_profit'));

        // Trading parameters
        if (formData.get('cooldown')) config.cooldown = parseInt(formData.get('cooldown'));
        if (formData.get('slippage')) config.slippage = parseFloat(formData.get('slippage'));
        config.compound_profits = formData.get('compound_profits') === 'on';

        // Notifications
        config.notify_on_trade = formData.get('notify_on_trade') === 'on';
        config.notify_on_error = formData.get('notify_on_error') === 'on';
        config.notify_on_stop = formData.get('notify_on_stop') === 'on';
        if (formData.get('notification_email')) config.notification_email = formData.get('notification_email');

        // Advanced settings
        if (formData.get('retry_attempts')) config.retry_attempts = parseInt(formData.get('retry_attempts'));
        if (formData.get('timeout')) config.timeout = parseInt(formData.get('timeout'));
        config.dry_run = formData.get('dry_run') === 'on';
        config.verbose_logging = formData.get('verbose_logging') === 'on';

        // Custom parameters
        const customParams = formData.get('custom_params');
        if (customParams && customParams.trim()) {
            try {
                config.custom_params = JSON.parse(customParams);
            } catch (error) {
                console.warn('Invalid custom parameters JSON:', error);
            }
        }

        return config;
    }
}

// Global instance
const botConfigModal = new BotConfigModal();
