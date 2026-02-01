class GitHubService {
    constructor(token) {
        this.token = token;
        this.baseUrl = 'https://api.github.com';
    }

    async createRepository(repoName, options = {}) {
        try {
            // Clear validation for repository name
            if (!repoName || typeof repoName !== 'string') {
                throw new Error('Repository name is required and must be a string');
            }

            if (repoName.length < 1 || repoName.length > 100) {
                throw new Error('Repository name must be between 1 and 100 characters');
            }

            if (!/^[a-zA-Z0-9._-]+$/.test(repoName)) {
                throw new Error('Repository name contains invalid characters. Use only letters, numbers, dots, hyphens, and underscores.');
            }

            const payload = {
                name: repoName,
                description: options.description || '',
                private: options.private || false,
                auto_init: options.autoInit || true,
                gitignore_template: options.gitignoreTemplate || null,
                license_template: options.licenseTemplate || null
            };

            const response = await fetch(`${this.baseUrl}/user/repos`, {
                method: 'POST',
                headers: {
                    'Authorization': `token ${this.token}`,
                    'Accept': 'application/vnd.github.v3+json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json();
                if (response.status === 422) {
                    throw new Error(`Repository creation failed: ${errorData.message}. The repository '${repoName}' may already exist.`);
                }
                throw new Error(`GitHub API error (${response.status}): ${errorData.message || 'Unknown error'}`);
            }

            const result = await response.json();
            return {
                success: true,
                repository: {
                    name: result.name,
                    fullName: result.full_name,
                    url: result.html_url,
                    cloneUrl: result.clone_url,
                    sshUrl: result.ssh_url
                },
                message: `Repository '${repoName}' created successfully`
            };

        } catch (error) {
            return {
                success: false,
                error: error.message,
                message: `Failed to create repository '${repoName}': ${error.message}`
            };
        }
    }
}