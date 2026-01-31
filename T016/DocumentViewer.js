class DocumentViewer {
    constructor(container) {
        this.container = container;
        this.documents = [];
        this.currentDocument = null;
        this.init();
    }

    init() {
        this.render();
        this.attachEventListeners();
    }

    render() {
        this.container.innerHTML = `
            <div class="document-viewer">
                <div class="document-header">
                    <h3>Documents</h3>
                    <button id="uploadBtn">Upload</button>
                </div>
                <div class="document-list" id="documentList"></div>
                <div class="document-preview" id="documentPreview">
                    <div class="no-document">Select a document to preview</div>
                </div>
            </div>
        `;
    }

    attachEventListeners() {
        const uploadBtn = document.getElementById('uploadBtn');
        uploadBtn.addEventListener('click', () => this.uploadDocument());
    }

    uploadDocument() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.pdf,.txt,.doc,.docx';
        
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                this.addDocument(file);
            }
        };
        
        input.click();
    }

    addDocument(file) {
        const document = {
            id: Date.now(),
            name: file.name,
            size: file.size,
            type: file.type,
            file: file,
            uploadDate: new Date()
        };
        
        this.documents.push(document);
        this.updateDocumentList();
        this.onDocumentAdded?.(document);
    }

    updateDocumentList() {
        const listContainer = document.getElementById('documentList');
        listContainer.innerHTML = this.documents.map(doc => `
            <div class="document-item" data-id="${doc.id}">
                <span class="doc-name">${doc.name}</span>
                <span class="doc-size">${this.formatFileSize(doc.size)}</span>
                <button onclick="documentViewer.viewDocument(${doc.id})">View</button>
            </div>
        `).join('');
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}