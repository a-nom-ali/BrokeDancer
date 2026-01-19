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

    editProfile(profileId) {
        showNotification('Profile editing UI coming soon!', 'info');
        // TODO: Implement edit UI with credential management
    }
}

// Global instance
const profileModal = new ProfileModal();
