async function copyMarkdown() {
    try {
        const response = await fetch(window.location.pathname + '/markdown');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const markdown = await response.text();

        // Try modern clipboard API first
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(markdown);
        } else {
            // Fallback for non-HTTPS environments
            const textArea = document.createElement('textarea');
            textArea.value = markdown;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
        }

        // Show feedback
        const button = event.target;
        const originalText = button.textContent;
        button.textContent = '✅ Copied!';
        setTimeout(() => {
            button.textContent = originalText;
        }, 2000);
    } catch (err) {
        console.error('Failed to copy markdown:', err);

        // If all else fails, show a popup with the markdown text
        try {
            const response = await fetch(window.location.pathname + '/markdown');
            const markdown = await response.text();

            // Create a modal dialog
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0,0,0,0.8); z-index: 10000; display: flex;
                justify-content: center; align-items: center;
            `;

            const content = document.createElement('div');
            content.style.cssText = `
                background: #333; padding: 20px; border-radius: 8px;
                width: 90%; max-width: 1200px; max-height: 80%; overflow: auto;
                position: relative;
            `;

            const closeBtn = document.createElement('button');
            closeBtn.textContent = '✕ Close';
            closeBtn.style.cssText = `
                position: absolute; top: 10px; right: 10px;
                background: #f44336; color: white; border: none;
                padding: 8px 16px; border-radius: 3px; cursor: pointer;
                font-size: 14px; width: 90px; white-space: nowrap;
                overflow: hidden;
            `;
            closeBtn.onclick = () => document.body.removeChild(modal);

            const copyBtn = document.createElement('button');
            copyBtn.textContent = '📋 Copy';
            copyBtn.style.cssText = `
                position: absolute; top: 10px; right: 120px;
                background: #4CAF50; color: white; border: none;
                padding: 8px 16px; border-radius: 3px; cursor: pointer;
                font-size: 14px; width: 90px; white-space: nowrap;
                overflow: hidden;
            `;
            copyBtn.onclick = async () => {
                try {
                    const textToCopy = textarea.value;
                    if (navigator.clipboard && window.isSecureContext) {
                        await navigator.clipboard.writeText(textToCopy);
                    } else {
                        textarea.select();
                        document.execCommand('copy');
                    }
                    const originalText = copyBtn.textContent;
                    copyBtn.textContent = '✅ Copied!';
                    setTimeout(() => {
                        copyBtn.textContent = originalText;
                    }, 2000);
                } catch (err) {
                    console.error('Failed to copy:', err);
                }
            };

            const textarea = document.createElement('textarea');
            textarea.value = markdown;
            textarea.style.cssText = `
                width: 100%; height: 400px; font-family: monospace;
                border: 1px solid #ccc; padding: 10px; margin-top: 30px;
                background: white !important; color: black !important;
            `;

            content.appendChild(closeBtn);
            content.appendChild(copyBtn);
            content.appendChild(textarea);
            modal.appendChild(content);
            document.body.appendChild(modal);

            // Close on background click
            modal.onclick = (e) => {
                if (e.target === modal) document.body.removeChild(modal);
            };

            const button = event.target;
            const originalText = button.textContent;
            button.textContent = '📄 Opened';
            setTimeout(() => {
                button.textContent = originalText;
            }, 2000);
        } catch (fallbackErr) {
            // Silently fail - user can try again if needed
        }
    }
}

async function copyURL(event) {
    try {
        const url = window.location.href;

        // Try modern clipboard API first
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(url);
        } else {
            // Fallback for non-HTTPS environments
            const textArea = document.createElement('textarea');
            textArea.value = url;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
        }

        // Show feedback
        const button = event.target;
        const originalText = button.textContent;
        button.textContent = '✅ Copied!';
        setTimeout(() => {
            button.textContent = originalText;
        }, 2000);
    } catch (err) {
        console.error('Failed to copy URL:', err);
        alert('Failed to copy URL: ' + err.message);
    }
}

async function copySourceURL(event) {
    try {
        // Convert path back to source URL (remove leading slash, add https://)
        const path = window.location.pathname;
        const sourceURL = 'https://' + path.substring(1);

        // Try modern clipboard API first
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(sourceURL);
        } else {
            // Fallback for non-HTTPS environments
            const textArea = document.createElement('textarea');
            textArea.value = sourceURL;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
        }

        // Show feedback
        const button = event.target;
        const originalText = button.textContent;
        button.textContent = '✅ Copied!';
        setTimeout(() => {
            button.textContent = originalText;
        }, 2000);
    } catch (err) {
        console.error('Failed to copy source URL:', err);
        alert('Failed to copy source URL: ' + err.message);
    }
}
