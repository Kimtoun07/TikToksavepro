document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;
    const currentYearSpan = document.getElementById('current-year');
    const downloadButton = document.getElementById('download-btn');
    const tiktokUrlInput = document.getElementById('tiktok-url');

    // --- Theme Toggle Logic ---
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        body.classList.add(savedTheme);
        if (savedTheme === 'dark-mode') {
            themeToggle.querySelector('i').classList.replace('fa-moon', 'fa-sun');
        }
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        // Default to dark mode if OS preference is dark
        body.classList.add('dark-mode');
        themeToggle.querySelector('i').classList.replace('fa-moon', 'fa-sun');
        localStorage.setItem('theme', 'dark-mode');
    }

    themeToggle.addEventListener('click', () => {
        if (body.classList.contains('dark-mode')) {
            body.classList.remove('dark-mode');
            themeToggle.querySelector('i').classList.replace('fa-sun', 'fa-moon');
            localStorage.setItem('theme', 'light-mode');
        } else {
            body.classList.add('dark-mode');
            themeToggle.querySelector('i').classList.replace('fa-moon', 'fa-sun');
            localStorage.setItem('theme', 'dark-mode');
        }
    });

    // --- Dynamic Current Year in Footer ---
    if (currentYearSpan) {
        currentYearSpan.textContent = new Date().getFullYear();
    }

    // --- Download Button Logic (Interacts with Backend) ---
    downloadButton.addEventListener('click', async () => {
        const url = tiktokUrlInput.value.trim();
        const originalButtonText = downloadButton.innerHTML; // Store original text

        if (!url) {
            alert('Please paste a TikTok video URL into the field.');
            return;
        }

        // Basic URL validation (more robust validation should be on backend too)
        if (!url.includes('tiktok.com') && !url.includes('douyin.com')) {
            alert('Please enter a valid TikTok or Douyin URL.');
            return;
        }

        // Disable button and show loading state
        downloadButton.disabled = true;
        downloadButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        tiktokUrlInput.disabled = true; // Disable input during processing

        try {
            const response = await fetch('/download-tiktok', { // Send request to your Flask backend
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ tiktokUrl: url }),
            });

            if (!response.ok) {
                // Attempt to parse server-sent error message
                const errorData = await response.json().catch(() => ({ message: 'Server error occurred.' }));
                throw new Error(errorData.message || 'Failed to process video.');
            }

            const data = await response.json();

            if (data.success && data.downloadLink) {
                // Initiate download by redirecting the browser
                window.location.href = data.downloadLink;
                // Optionally clear the input after successful download trigger
                tiktokUrlInput.value = '';
            } else {
                // Handle backend-specific errors (e.g., video not found, processing failed)
                throw new Error(data.message || 'Could not get download link.');
            }

        } catch (error) {
            console.error('Download error:', error);
            alert(`Error: ${error.message || 'An unknown error occurred while trying to download the video. Please try again.'}`);
        } finally {
            // Re-enable button and restore text
            downloadButton.disabled = false;
            downloadButton.innerHTML = originalButtonText;
            tiktokUrlInput.disabled = false; // Re-enable input
        }
    });
});