document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.getElementById('menu-toggle');
    const menuClose = document.getElementById('menu-close');
    const sideMenu = document.getElementById('side-menu');
    const overlay = document.getElementById('menu-overlay');
    const menuLinks = sideMenu.querySelectorAll('a, button');
    
    // State
    let isMenuOpen = false;

    // Toggle Menu Function
    function toggleMenu(open) {
        isMenuOpen = open;
        
        if (open) {
            sideMenu.classList.add('open');
            overlay.classList.add('visible');
            sideMenu.setAttribute('aria-hidden', 'false');
            menuToggle.setAttribute('aria-expanded', 'true');
            overlay.setAttribute('aria-hidden', 'false');
            
            // Focus Trap: focus first element
            if (menuLinks.length > 0) {
                // Slight delay to allow transition to start/render
                setTimeout(() => menuClose.focus(), 50);
            }
        } else {
            sideMenu.classList.remove('open');
            overlay.classList.remove('visible');
            sideMenu.setAttribute('aria-hidden', 'true');
            menuToggle.setAttribute('aria-expanded', 'false');
            overlay.setAttribute('aria-hidden', 'true');
            
            // Return focus to toggle button
            menuToggle.focus();
        }
    }

    // Event Listeners
    menuToggle.addEventListener('click', () => toggleMenu(true));
    menuClose.addEventListener('click', () => toggleMenu(false));
    overlay.addEventListener('click', () => toggleMenu(false));

    // Keyboard Accessibility
    document.addEventListener('keydown', (e) => {
        if (!isMenuOpen) return;

        // Close on Escape
        if (e.key === 'Escape') {
            toggleMenu(false);
        }

        // Focus Trap Logic
        if (e.key === 'Tab') {
            const firstElement = menuClose; // Close button is first focusable
            const lastElement = menuLinks[menuLinks.length - 1]; // Last link

            if (e.shiftKey) {
                // Shift + Tab
                if (document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                }
            } else {
                // Tab
                if (document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        }
    });

    // Handle Resize (Reset state on switch to desktop)
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            if (isMenuOpen) {
                // Reset internal state but keep visual correctness (CSS handles visibility)
                sideMenu.classList.remove('open');
                overlay.classList.remove('visible');
                sideMenu.setAttribute('aria-hidden', 'false'); // Always visible on desktop
                isMenuOpen = false;
            } else {
                sideMenu.setAttribute('aria-hidden', 'false');
            }
        } else {
            // Mobile mode: ensure aria-hidden is correct based on state
            if (!isMenuOpen) {
                sideMenu.setAttribute('aria-hidden', 'true');
            }
        }
    });

    // Initial check
    if (window.innerWidth > 768) {
        sideMenu.setAttribute('aria-hidden', 'false');
    }
});
