// src/web/static/js/components/strategy-builder-modal.js

class StrategyBuilderModal {
    constructor() {
        this.modal = null;
    }

    show() {
        this.render();
        this.modal.style.display = 'flex';

        // Initialize strategy builder
        setTimeout(() => {
            strategyBuilder = new StrategyBuilder('strategyBuilderContainer');
        }, 100);
    }

    hide() {
        if (this.modal) {
            this.modal.style.display = 'none';
            this.modal.remove();
            strategyBuilder = null;
        }
    }

    render() {
        // Remove existing modal if any
        const existing = document.getElementById('strategyBuilderModal');
        if (existing) existing.remove();

        this.modal = document.createElement('div');
        this.modal.id = 'strategyBuilderModal';
        this.modal.className = 'fullscreen-modal';
        this.modal.innerHTML = `
            <div class="fullscreen-modal__header">
                <h2>🎨 Visual Strategy Builder</h2>
                <button class="modal-close" onclick="strategyBuilderModal.hide()">×</button>
            </div>
            <div class="fullscreen-modal__body">
                <div id="strategyBuilderContainer"></div>
            </div>
        `;

        document.body.appendChild(this.modal);

        // Close on background click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                if (confirm('Close strategy builder? Any unsaved changes will be lost.')) {
                    this.hide();
                }
            }
        });

        // Prevent escape key from closing (since it's a complex tool)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal && this.modal.style.display === 'flex') {
                if (confirm('Close strategy builder? Any unsaved changes will be lost.')) {
                    this.hide();
                }
                e.preventDefault();
            }
        });
    }
}

// Global instance
const strategyBuilderModal = new StrategyBuilderModal();
