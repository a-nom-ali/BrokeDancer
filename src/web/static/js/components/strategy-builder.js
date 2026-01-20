// src/web/static/js/components/strategy-builder.js

/**
 * Visual Strategy Builder Component
 *
 * Drag-and-drop interface for creating trading strategies without code.
 * Supports triggers, conditions, actions, and risk management blocks.
 */

class StrategyBuilder {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.canvas = null;
        this.blocks = [];
        this.connections = [];
        this.selectedBlock = null;
        this.draggedBlock = null;
        this.offset = { x: 0, y: 0 };

        // Block types library
        this.blockLibrary = {
            triggers: [
                { id: 'price_cross', name: 'Price Cross', icon: '📈', inputs: ['price', 'threshold'], outputs: ['signal'] },
                { id: 'volume_spike', name: 'Volume Spike', icon: '📊', inputs: ['volume', 'multiplier'], outputs: ['signal'] },
                { id: 'time_trigger', name: 'Time Trigger', icon: '⏰', inputs: ['schedule'], outputs: ['signal'] },
                { id: 'rsi_signal', name: 'RSI Signal', icon: '📉', inputs: ['period', 'overbought', 'oversold'], outputs: ['signal'] }
            ],
            conditions: [
                { id: 'and', name: 'AND Gate', icon: '&', inputs: ['input1', 'input2'], outputs: ['output'] },
                { id: 'or', name: 'OR Gate', icon: '|', inputs: ['input1', 'input2'], outputs: ['output'] },
                { id: 'compare', name: 'Compare', icon: '=', inputs: ['value1', 'operator', 'value2'], outputs: ['result'] },
                { id: 'threshold', name: 'Threshold', icon: '🎚', inputs: ['value', 'min', 'max'], outputs: ['pass'] }
            ],
            actions: [
                { id: 'buy', name: 'Buy Order', icon: '💰', inputs: ['signal', 'amount'], outputs: ['order'] },
                { id: 'sell', name: 'Sell Order', icon: '💵', inputs: ['signal', 'amount'], outputs: ['order'] },
                { id: 'cancel', name: 'Cancel Orders', icon: '❌', inputs: ['signal'], outputs: ['done'] },
                { id: 'notify', name: 'Send Alert', icon: '🔔', inputs: ['signal', 'message'], outputs: ['sent'] }
            ],
            risk: [
                { id: 'stop_loss', name: 'Stop Loss', icon: '🛑', inputs: ['price', 'percentage'], outputs: ['trigger'] },
                { id: 'take_profit', name: 'Take Profit', icon: '🎯', inputs: ['price', 'percentage'], outputs: ['trigger'] },
                { id: 'position_size', name: 'Position Size', icon: '📏', inputs: ['capital', 'risk_pct'], outputs: ['size'] },
                { id: 'max_trades', name: 'Max Trades', icon: '🔢', inputs: ['limit'], outputs: ['allowed'] }
            ]
        };

        this.init();
    }

    init() {
        this.render();
        this.attachEventListeners();
    }

    render() {
        this.container.innerHTML = `
            <div class="strategy-builder">
                <!-- Toolbar -->
                <div class="strategy-builder__toolbar">
                    <div class="toolbar__section">
                        <button class="toolbar__btn" onclick="strategyBuilder.newStrategy()" title="New Strategy">
                            📄 New
                        </button>
                        <button class="toolbar__btn" onclick="strategyBuilder.loadTemplate()" title="Load Template">
                            📋 Templates
                        </button>
                        <button class="toolbar__btn" onclick="strategyBuilder.save()" title="Save Strategy">
                            💾 Save
                        </button>
                    </div>
                    <div class="toolbar__section">
                        <button class="toolbar__btn" onclick="strategyBuilder.validate()" title="Validate Strategy">
                            ✓ Validate
                        </button>
                        <button class="toolbar__btn" onclick="strategyBuilder.generateCode()" title="Generate Code">
                            🔧 Generate
                        </button>
                        <button class="toolbar__btn toolbar__btn--primary" onclick="strategyBuilder.deploy()" title="Deploy Strategy">
                            🚀 Deploy
                        </button>
                    </div>
                </div>

                <!-- Main Layout -->
                <div class="strategy-builder__main">
                    <!-- Block Library Sidebar -->
                    <div class="strategy-builder__sidebar">
                        <h3>Building Blocks</h3>

                        <div class="block-category">
                            <div class="block-category__header" onclick="this.parentElement.classList.toggle('collapsed')">
                                <span>📈 Triggers</span>
                                <span class="block-category__toggle">▼</span>
                            </div>
                            <div class="block-category__content">
                                ${this.renderBlockLibrary('triggers')}
                            </div>
                        </div>

                        <div class="block-category">
                            <div class="block-category__header" onclick="this.parentElement.classList.toggle('collapsed')">
                                <span>🔀 Conditions</span>
                                <span class="block-category__toggle">▼</span>
                            </div>
                            <div class="block-category__content">
                                ${this.renderBlockLibrary('conditions')}
                            </div>
                        </div>

                        <div class="block-category">
                            <div class="block-category__header" onclick="this.parentElement.classList.toggle('collapsed')">
                                <span>⚡ Actions</span>
                                <span class="block-category__toggle">▼</span>
                            </div>
                            <div class="block-category__content">
                                ${this.renderBlockLibrary('actions')}
                            </div>
                        </div>

                        <div class="block-category">
                            <div class="block-category__header" onclick="this.parentElement.classList.toggle('collapsed')">
                                <span>🛡️ Risk Management</span>
                                <span class="block-category__toggle">▼</span>
                            </div>
                            <div class="block-category__content">
                                ${this.renderBlockLibrary('risk')}
                            </div>
                        </div>
                    </div>

                    <!-- Canvas -->
                    <div class="strategy-builder__canvas-wrapper">
                        <div class="canvas__controls">
                            <button class="canvas__btn" onclick="strategyBuilder.zoomIn()" title="Zoom In">+</button>
                            <button class="canvas__btn" onclick="strategyBuilder.zoomOut()" title="Zoom Out">−</button>
                            <button class="canvas__btn" onclick="strategyBuilder.resetZoom()" title="Reset View">⊙</button>
                            <button class="canvas__btn" onclick="strategyBuilder.clearCanvas()" title="Clear All">🗑</button>
                        </div>
                        <canvas id="strategyCanvas" class="strategy-builder__canvas"></canvas>
                        <div class="canvas__hint">
                            Drag blocks from the sidebar to start building your strategy
                        </div>
                    </div>

                    <!-- Properties Panel -->
                    <div class="strategy-builder__properties">
                        <h3>Properties</h3>
                        <div id="propertiesPanel" class="properties__content">
                            <p class="properties__empty">Select a block to edit its properties</p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.canvas = document.getElementById('strategyCanvas');
        this.setupCanvas();
    }

    renderBlockLibrary(category) {
        return this.blockLibrary[category].map(block => `
            <div class="block-library__item"
                 draggable="true"
                 data-block-type="${block.id}"
                 data-category="${category}">
                <span class="block__icon">${block.icon}</span>
                <span class="block__name">${block.name}</span>
            </div>
        `).join('');
    }

    setupCanvas() {
        const wrapper = this.canvas.parentElement;
        this.canvas.width = wrapper.clientWidth;
        this.canvas.height = wrapper.clientHeight;

        this.ctx = this.canvas.getContext('2d');
        this.drawGrid();
    }

    drawGrid() {
        const ctx = this.ctx;
        const gridSize = 20;

        ctx.strokeStyle = 'rgba(100, 116, 139, 0.1)';
        ctx.lineWidth = 1;

        // Vertical lines
        for (let x = 0; x < this.canvas.width; x += gridSize) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, this.canvas.height);
            ctx.stroke();
        }

        // Horizontal lines
        for (let y = 0; y < this.canvas.height; y += gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(this.canvas.width, y);
            ctx.stroke();
        }
    }

    attachEventListeners() {
        // Library item drag events
        const libraryItems = this.container.querySelectorAll('.block-library__item');
        libraryItems.forEach(item => {
            item.addEventListener('dragstart', (e) => this.handleDragStart(e));
            item.addEventListener('dragend', (e) => this.handleDragEnd(e));
        });

        // Canvas drop events
        this.canvas.addEventListener('dragover', (e) => e.preventDefault());
        this.canvas.addEventListener('drop', (e) => this.handleDrop(e));

        // Canvas click events
        this.canvas.addEventListener('click', (e) => this.handleCanvasClick(e));

        // Window resize
        window.addEventListener('resize', () => this.setupCanvas());
    }

    handleDragStart(e) {
        const blockType = e.target.dataset.blockType;
        const category = e.target.dataset.category;

        e.dataTransfer.effectAllowed = 'copy';
        e.dataTransfer.setData('blockType', blockType);
        e.dataTransfer.setData('category', category);

        e.target.classList.add('dragging');
    }

    handleDragEnd(e) {
        e.target.classList.remove('dragging');
    }

    handleDrop(e) {
        e.preventDefault();

        const blockType = e.dataTransfer.getData('blockType');
        const category = e.dataTransfer.getData('category');

        if (!blockType || !category) return;

        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        this.addBlock(blockType, category, x, y);
    }

    addBlock(blockType, category, x, y) {
        const template = this.blockLibrary[category].find(b => b.id === blockType);
        if (!template) return;

        const block = {
            id: `block_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            type: blockType,
            category: category,
            name: template.name,
            icon: template.icon,
            x: x,
            y: y,
            width: 150,
            height: 80,
            inputs: template.inputs.map(name => ({ name, connected: false })),
            outputs: template.outputs.map(name => ({ name, connected: false })),
            properties: {}
        };

        this.blocks.push(block);
        this.redraw();

        showNotification(`Added ${block.name}`, 'success');
    }

    handleCanvasClick(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Check if clicked on a block
        const clickedBlock = this.blocks.find(block =>
            x >= block.x && x <= block.x + block.width &&
            y >= block.y && y <= block.y + block.height
        );

        if (clickedBlock) {
            this.selectBlock(clickedBlock);
        } else {
            this.deselectBlock();
        }
    }

    selectBlock(block) {
        this.selectedBlock = block;
        this.redraw();
        this.showProperties(block);
    }

    deselectBlock() {
        this.selectedBlock = null;
        this.redraw();
        this.hideProperties();
    }

    showProperties(block) {
        const panel = document.getElementById('propertiesPanel');

        panel.innerHTML = `
            <div class="property-group">
                <label>Block Type</label>
                <input type="text" value="${block.name}" readonly>
            </div>
            <div class="property-group">
                <label>Block ID</label>
                <input type="text" value="${block.id}" readonly>
            </div>
            <div class="property-group">
                <label>Category</label>
                <input type="text" value="${block.category}" readonly>
            </div>
            <hr>
            <h4>Settings</h4>
            ${this.renderBlockProperties(block)}
            <button class="btn btn--danger" onclick="strategyBuilder.deleteBlock('${block.id}')" style="width: 100%; margin-top: 10px;">
                Delete Block
            </button>
        `;
    }

    renderBlockProperties(block) {
        // Generate property inputs based on block type
        const inputs = block.inputs.map((input, i) => `
            <div class="property-group">
                <label>${input.name}</label>
                <input type="text"
                       placeholder="Enter ${input.name}"
                       value="${block.properties[input.name] || ''}"
                       onchange="strategyBuilder.updateProperty('${block.id}', '${input.name}', this.value)">
            </div>
        `).join('');

        return inputs || '<p class="properties__empty">No configurable properties</p>';
    }

    updateProperty(blockId, propertyName, value) {
        const block = this.blocks.find(b => b.id === blockId);
        if (block) {
            block.properties[propertyName] = value;
        }
    }

    hideProperties() {
        const panel = document.getElementById('propertiesPanel');
        panel.innerHTML = '<p class="properties__empty">Select a block to edit its properties</p>';
    }

    deleteBlock(blockId) {
        if (!confirm('Delete this block?')) return;

        this.blocks = this.blocks.filter(b => b.id !== blockId);
        this.connections = this.connections.filter(c =>
            c.from.blockId !== blockId && c.to.blockId !== blockId
        );

        this.deselectBlock();
        this.redraw();

        showNotification('Block deleted', 'info');
    }

    redraw() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw grid
        this.drawGrid();

        // Draw connections
        this.connections.forEach(conn => this.drawConnection(conn));

        // Draw blocks
        this.blocks.forEach(block => this.drawBlock(block));
    }

    drawBlock(block) {
        const ctx = this.ctx;
        const isSelected = this.selectedBlock && this.selectedBlock.id === block.id;

        // Block shadow
        if (isSelected) {
            ctx.shadowColor = 'rgba(59, 130, 246, 0.5)';
            ctx.shadowBlur = 10;
        }

        // Block background
        ctx.fillStyle = isSelected ? '#1e40af' : '#334155';
        ctx.fillRect(block.x, block.y, block.width, block.height);

        // Block border
        ctx.strokeStyle = isSelected ? '#3b82f6' : '#475569';
        ctx.lineWidth = isSelected ? 3 : 2;
        ctx.strokeRect(block.x, block.y, block.width, block.height);

        ctx.shadowBlur = 0;

        // Block header
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(block.x, block.y, block.width, 30);

        // Block icon and name
        ctx.fillStyle = '#f1f5f9';
        ctx.font = '16px sans-serif';
        ctx.fillText(block.icon, block.x + 10, block.y + 20);

        ctx.font = '12px sans-serif';
        ctx.fillStyle = '#e2e8f0';
        ctx.fillText(block.name, block.x + 35, block.y + 20);

        // Input/Output ports
        this.drawPorts(block);
    }

    drawPorts(block) {
        const ctx = this.ctx;
        const portRadius = 5;

        // Input ports (left side)
        block.inputs.forEach((input, i) => {
            const y = block.y + 40 + (i * 20);

            ctx.fillStyle = input.connected ? '#10b981' : '#64748b';
            ctx.beginPath();
            ctx.arc(block.x, y, portRadius, 0, 2 * Math.PI);
            ctx.fill();

            ctx.fillStyle = '#94a3b8';
            ctx.font = '10px sans-serif';
            ctx.fillText(input.name, block.x + 10, y + 4);
        });

        // Output ports (right side)
        block.outputs.forEach((output, i) => {
            const y = block.y + 40 + (i * 20);

            ctx.fillStyle = output.connected ? '#10b981' : '#64748b';
            ctx.beginPath();
            ctx.arc(block.x + block.width, y, portRadius, 0, 2 * Math.PI);
            ctx.fill();

            ctx.fillStyle = '#94a3b8';
            ctx.font = '10px sans-serif';
            const text = output.name;
            const textWidth = ctx.measureText(text).width;
            ctx.fillText(text, block.x + block.width - textWidth - 10, y + 4);
        });
    }

    drawConnection(conn) {
        const ctx = this.ctx;

        ctx.strokeStyle = '#3b82f6';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(conn.from.x, conn.from.y);

        // Bezier curve for smooth connection
        const cp1x = conn.from.x + 50;
        const cp1y = conn.from.y;
        const cp2x = conn.to.x - 50;
        const cp2y = conn.to.y;

        ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, conn.to.x, conn.to.y);
        ctx.stroke();
    }

    // Toolbar actions
    newStrategy() {
        if (this.blocks.length > 0 && !confirm('Clear current strategy?')) return;

        this.blocks = [];
        this.connections = [];
        this.deselectBlock();
        this.redraw();

        showNotification('New strategy canvas ready', 'info');
    }

    loadTemplate() {
        showNotification('Template selector coming soon!', 'info');
        // TODO: Show template modal
    }

    save() {
        const strategy = {
            blocks: this.blocks,
            connections: this.connections,
            timestamp: new Date().toISOString()
        };

        const json = JSON.stringify(strategy, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `strategy_${Date.now()}.json`;
        a.click();

        showNotification('Strategy saved!', 'success');
    }

    validate() {
        const errors = [];

        // Check for triggers
        const hasTrigger = this.blocks.some(b => b.category === 'triggers');
        if (!hasTrigger) {
            errors.push('Strategy must have at least one trigger');
        }

        // Check for actions
        const hasAction = this.blocks.some(b => b.category === 'actions');
        if (!hasAction) {
            errors.push('Strategy must have at least one action');
        }

        // Check for disconnected blocks
        const disconnectedBlocks = this.blocks.filter(b =>
            b.outputs.every(o => !o.connected)
        );
        if (disconnectedBlocks.length > 0 && this.blocks.length > 1) {
            errors.push(`${disconnectedBlocks.length} block(s) are not connected`);
        }

        if (errors.length > 0) {
            showNotification(`Validation failed:\n${errors.join('\n')}`, 'error');
        } else {
            showNotification('✓ Strategy is valid!', 'success');
        }

        return errors.length === 0;
    }

    generateCode() {
        if (!this.validate()) return;

        showNotification('Code generation coming soon!', 'info');
        // TODO: Generate Python strategy code from blocks
    }

    deploy() {
        if (!this.validate()) return;

        if (!confirm('Deploy this strategy to production?')) return;

        showNotification('Strategy deployment coming soon!', 'info');
        // TODO: Deploy strategy to bot
    }

    // Canvas controls
    zoomIn() {
        showNotification('Zoom coming soon!', 'info');
    }

    zoomOut() {
        showNotification('Zoom coming soon!', 'info');
    }

    resetZoom() {
        this.redraw();
    }

    clearCanvas() {
        this.newStrategy();
    }
}

// Global instance will be created when modal opens
let strategyBuilder = null;
