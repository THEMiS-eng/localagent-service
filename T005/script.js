document.addEventListener('DOMContentLoaded', function() {
    const accordionHeaders = document.querySelectorAll('.accordion-header');
    
    accordionHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const targetContent = document.getElementById(targetId);
            const isActive = this.classList.contains('active');
            
            // Close all accordion items
            accordionHeaders.forEach(h => {
                h.classList.remove('active');
                const contentId = h.getAttribute('data-target');
                const content = document.getElementById(contentId);
                content.classList.remove('active');
            });
            
            // If the clicked item wasn't active, open it
            if (!isActive) {
                this.classList.add('active');
                targetContent.classList.add('active');
            }
        });
    });
    
    // Optional: Open first accordion item by default
    const firstHeader = accordionHeaders[0];
    if (firstHeader) {
        const firstTargetId = firstHeader.getAttribute('data-target');
        const firstContent = document.getElementById(firstTargetId);
        firstHeader.classList.add('active');
        firstContent.classList.add('active');
    }
});