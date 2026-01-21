// src/web/static/js/components/profile-modal.js

class ProfileModal {
    constructor() {
        this.modal = null;
        this.profiles = [];
        this.activeProfile = null;
    }

    async show() {
        await this.loadProfiles();
        this.render();
        this.modal.style.display = 'flex';
    }

    hide() {
        if (this.modal) {
            this.modal.style.display = 'none';
        }
    }

    async loadProfiles() {
        try {
            const response = await fetch('/api/profiles');
            this.profiles = await response.json();

            const activeResponse = await fetch('/api/profiles/active');
            this.activeProfile = await activeResponse.json();
        } catch (error) {
            console.error('Error loading profiles:', error);
        }
    }

    render() {
        // Remove existing modal if any
        const existing = document.getElementById('profileModal');
        if (existing) existing.remove();

        this.modal = document.createElement('div');
        this.modal.id = 'profileModal';
        this.modal.className = 'modal';
        this.modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>👤 Trading Profiles</h2>
                    <button class="modal-close" onclick="profileModal.hide()">×</button>
                </div>
                <div class="modal-body">
                    <div class="profile-list">
                        ${this.renderProfileList()}
                    </div>
                    <button class="btn btn--primary" onclick="profileModal.showCreateForm()" style="width: 100%; margin-top: 20px;">
                        + Create New Profile
                    </button>
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

    renderProfileList() {
        if (this.profiles.length === 0) {
            return '<p style="text-align: center; color: var(--text-tertiary); padding: 40px;">No profiles yet. Create your first profile to get started!</p>';
        }

        return this.profiles.map(profile => {
            const isActive = this.activeProfile && this.activeProfile.id === profile.id;
            return `
                <div class="profile-item ${isActive ? 'profile-item--active' : ''}">
                    <div class="profile-item__info">
                        <div class="profile-item__name">
                            ${profile.name}
                            ${isActive ? '<span class="profile-badge">ACTIVE</span>' : ''}
                        </div>
                        <div class="profile-item__meta">
                            Created: ${new Date(profile.created_at).toLocaleDateString()}
                            ${profile.encrypted ? ' • 🔒 Encrypted' : ''}
                        </div>
                    </div>
                    <div class="profile-item__actions">
                        ${!isActive ? `<button class="btn btn--small btn--success" onclick="profileModal.activateProfile('${profile.id}')">Activate</button>` : ''}
                        <button class="btn btn--small" onclick="profileModal.editProfile('${profile.id}')">Edit</button>
                        ${!isActive ? `<button class="btn btn--small btn--danger" onclick="profileModal.deleteProfile('${profile.id}')">Delete</button>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    showCreateForm() {
        this.modal.querySelector('.modal-body').innerHTML = `
            <form id="createProfileForm" onsubmit="profileModal.createProfile(event)">
                <div class="form-group">
                    <label>Profile Name</label>
                    <input type="text" name="name" required placeholder="e.g., Production, Staging, Test">
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn--secondary" onclick="profileModal.show()">Cancel</button>
                    <button type="submit" class="btn btn--primary">Create Profile</button>
                </div>
            </form>
        `;
    }

    async createProfile(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        const name = formData.get('name');

        try {
            const response = await fetch('/api/profiles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, config: {} })
            });

            const result = await response.json();

            if (response.ok) {
                showNotification('Profile created successfully!', 'success');
                this.show(); // Reload list
            } else {
                showNotification(result.error || 'Failed to create profile', 'error');
            }
        } catch (error) {
            console.error('Error creating profile:', error);
            showNotification('Error creating profile', 'error');
        }
    }

    async activateProfile(profileId) {
        try {
            const response = await fetch(`/api/profiles/${profileId}/activate`, {
                method: 'POST'
            });

            if (response.ok) {
                showNotification('Profile activated successfully!', 'success');
                this.show(); // Reload list
                // Emit event for other components
                window.dispatchEvent(new CustomEvent('profile-activated', { detail: { profileId } }));
            } else {
                const result = await response.json();
                showNotification(result.error || 'Failed to activate profile', 'error');
            }
        } catch (error) {
            console.error('Error activating profile:', error);
            showNotification('Error activating profile', 'error');
        }
    }

    async deleteProfile(profileId) {
        if (!confirm('Are you sure you want to delete this profile? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`/api/profiles/${profileId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                showNotification('Profile deleted successfully!', 'success');
                this.show(); // Reload list
            } else {
                const result = await response.json();
                showNotification(result.error || 'Failed to delete profile', 'error');
            }
        } catch (error) {
            console.error('Error deleting profile:', error);
            showNotification('Error deleting profile', 'error');
        }
    }

    async editProfile(profileId) {
        try {
            // Load profile details
            const response = await fetch(`/api/profiles/${profileId}`);
            const profile = await response.json();

            this.showEditForm(profile);
        } catch (error) {
            console.error('Error loading profile:', error);
            showNotification('❌ Failed to load profile details', 'error');
        }
    }

    showEditForm(profile) {
        this.modal.querySelector('.modal-body').innerHTML = `
            <form id="editProfileForm" onsubmit="profileModal.updateProfile(event, '${profile.id}')">
                <div class="form-group">
                    <label>Profile Name</label>
                    <input type="text" name="name" value="${profile.name}" required>
                </div>

                <div class="config-section">
                    <h3>🔐 Credentials</h3>
                    <p class="security-notice">
                        <strong>Security Notice:</strong> Credentials are encrypted at rest.
                        Leave fields blank to keep existing values.
                    </p>

                    <div class="form-group">
                        <label>API Key</label>
                        <div class="credential-input-group">
                            <input type="password" name="api_key" placeholder="Enter new API key or leave blank">
                            <button type="button" class="btn-toggle-visibility" onclick="profileModal.togglePasswordVisibility(this)">
                                👁️
                            </button>
                        </div>
                        <small>Polymarket API key for trading</small>
                    </div>

                    <div class="form-group">
                        <label>API Secret</label>
                        <div class="credential-input-group">
                            <input type="password" name="api_secret" placeholder="Enter new API secret or leave blank">
                            <button type="button" class="btn-toggle-visibility" onclick="profileModal.togglePasswordVisibility(this)">
                                👁️
                            </button>
                        </div>
                        <small>Polymarket API secret for signing requests</small>
                    </div>

                    <div class="form-group">
                        <label>Wallet Private Key (Optional)</label>
                        <div class="credential-input-group">
                            <input type="password" name="private_key" placeholder="Enter wallet private key or leave blank">
                            <button type="button" class="btn-toggle-visibility" onclick="profileModal.togglePasswordVisibility(this)">
                                👁️
                            </button>
                        </div>
                        <small>Only required for on-chain operations</small>
                    </div>

                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="enable_encryption" ${profile.encrypted ? 'checked' : ''}>
                            Enable credential encryption (recommended)
                        </label>
                    </div>
                </div>

                <div class="config-section">
                    <h3>⚙️ Configuration</h3>

                    <div class="form-group">
                        <label>RPC URL</label>
                        <input type="url" name="rpc_url" value="${profile.config?.rpc_url || ''}" placeholder="https://polygon-rpc.com">
                        <small>Polygon RPC endpoint for blockchain operations</small>
                    </div>

                    <div class="form-group">
                        <label>Chain ID</label>
                        <input type="number" name="chain_id" value="${profile.config?.chain_id || 137}" placeholder="137">
                        <small>137 for Polygon Mainnet, 80001 for Mumbai Testnet</small>
                    </div>

                    <div class="form-group">
                        <label>Default Market</label>
                        <input type="text" name="default_market" value="${profile.config?.default_market || ''}" placeholder="Market ID">
                        <small>Default market for trading bots (optional)</small>
                    </div>

                    <div class="form-row">
                        <div class="form-col">
                            <label>Max Gas Price (Gwei)</label>
                            <input type="number" name="max_gas_price" value="${profile.config?.max_gas_price || ''}" placeholder="50" step="0.1">
                        </div>
                        <div class="form-col">
                            <label>Gas Limit</label>
                            <input type="number" name="gas_limit" value="${profile.config?.gas_limit || ''}" placeholder="200000">
                        </div>
                    </div>

                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="testnet_mode" ${profile.config?.testnet_mode ? 'checked' : ''}>
                            Testnet Mode (use Mumbai testnet instead of mainnet)
                        </label>
                    </div>
                </div>

                <div class="config-section config-section--collapsible collapsed">
                    <h3 onclick="this.parentElement.classList.toggle('collapsed')">
                        Advanced Settings
                        <span class="collapse-icon">▼</span>
                    </h3>
                    <div class="config-section__content">
                        <div class="form-group">
                            <label>Request Timeout (seconds)</label>
                            <input type="number" name="request_timeout" value="${profile.config?.request_timeout || 30}" placeholder="30">
                        </div>

                        <div class="form-group">
                            <label>Max Retries</label>
                            <input type="number" name="max_retries" value="${profile.config?.max_retries || 3}" placeholder="3">
                        </div>

                        <div class="form-group">
                            <label>
                                <input type="checkbox" name="verbose_logging" ${profile.config?.verbose_logging ? 'checked' : ''}>
                                Enable verbose logging
                            </label>
                        </div>

                        <div class="form-group">
                            <label>Custom Headers (JSON)</label>
                            <textarea name="custom_headers" rows="3" placeholder='{"X-Custom-Header": "value"}'>${profile.config?.custom_headers ? JSON.stringify(profile.config.custom_headers, null, 2) : ''}</textarea>
                        </div>
                    </div>
                </div>

                <div class="form-actions">
                    <button type="button" class="btn btn--secondary" onclick="profileModal.show()">Cancel</button>
                    <button type="button" class="btn btn--danger" onclick="profileModal.testConnection('${profile.id}')">
                        🔌 Test Connection
                    </button>
                    <button type="submit" class="btn btn--primary">Save Changes</button>
                </div>
            </form>
        `;
    }

    async updateProfile(event, profileId) {
        event.preventDefault();
        const formData = new FormData(event.target);

        // Build credentials object (only include if provided)
        const credentials = {};
        if (formData.get('api_key')) credentials.api_key = formData.get('api_key');
        if (formData.get('api_secret')) credentials.api_secret = formData.get('api_secret');
        if (formData.get('private_key')) credentials.private_key = formData.get('private_key');

        // Build config object
        const config = {
            rpc_url: formData.get('rpc_url'),
            chain_id: parseInt(formData.get('chain_id') || 137),
            default_market: formData.get('default_market'),
            testnet_mode: formData.get('testnet_mode') === 'on',
            max_gas_price: formData.get('max_gas_price') ? parseFloat(formData.get('max_gas_price')) : null,
            gas_limit: formData.get('gas_limit') ? parseInt(formData.get('gas_limit')) : null,
            request_timeout: parseInt(formData.get('request_timeout') || 30),
            max_retries: parseInt(formData.get('max_retries') || 3),
            verbose_logging: formData.get('verbose_logging') === 'on'
        };

        // Parse custom headers if provided
        const customHeaders = formData.get('custom_headers');
        if (customHeaders && customHeaders.trim()) {
            try {
                config.custom_headers = JSON.parse(customHeaders);
            } catch (error) {
                showNotification('❌ Invalid JSON in custom headers', 'error');
                return;
            }
        }

        const updateData = {
            name: formData.get('name'),
            config: config,
            enable_encryption: formData.get('enable_encryption') === 'on'
        };

        // Only include credentials if any were provided
        if (Object.keys(credentials).length > 0) {
            updateData.credentials = credentials;
        }

        try {
            const response = await fetch(`/api/profiles/${profileId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updateData)
            });

            const result = await response.json();

            if (response.ok) {
                showNotification('✅ Profile updated successfully!', 'success');
                this.show(); // Return to list
            } else {
                showNotification(`❌ ${result.error || 'Failed to update profile'}`, 'error');
            }
        } catch (error) {
            console.error('Error updating profile:', error);
            showNotification('❌ Error updating profile', 'error');
        }
    }

    async testConnection(profileId) {
        showNotification('🔌 Testing connection...', 'info');

        try {
            const response = await fetch(`/api/profiles/${profileId}/test`, {
                method: 'POST'
            });

            const result = await response.json();

            if (response.ok && result.success) {
                showNotification(`✅ Connection successful! ${result.message || ''}`, 'success');
            } else {
                showNotification(`❌ Connection failed: ${result.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error('Error testing connection:', error);
            showNotification('❌ Failed to test connection', 'error');
        }
    }

    togglePasswordVisibility(button) {
        const input = button.previousElementSibling;
        if (input.type === 'password') {
            input.type = 'text';
            button.textContent = '🙈';
        } else {
            input.type = 'password';
            button.textContent = '👁️';
        }
    }
}

// Global instance
const profileModal = new ProfileModal();
