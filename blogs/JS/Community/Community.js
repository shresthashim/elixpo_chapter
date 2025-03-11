document.addEventListener('DOMContentLoaded', function () {
    const bellIcon = document.querySelector('.bell-icon');
    const notificationsPanel = document.getElementById('notificationsPanel');
    const closeButton = document.querySelector('.close-button');

    // Add this near the top of your existing code
    const searchContainer = document.querySelector('.search-container');
    const searchInput = document.querySelector('.search-input');

    // Handle search input focus
    searchInput.addEventListener('focus', function () {
        searchContainer.classList.add('expanded');
    });

    // Close search suggestions when clicking outside
    document.addEventListener('click', function (e) {
        if (!searchContainer.contains(e.target)) {
            searchContainer.classList.remove('expanded');
        }
    });

    // Handle trending item clicks
    document.querySelectorAll('.trending-item').forEach(item => {
        item.addEventListener('click', function () {
            searchInput.value = this.querySelector('span').textContent;
        });
    });

    // Toggle notifications panel when bell icon is clicked
    bellIcon.addEventListener('click', function (e) {
        e.stopPropagation();
        if (notificationsPanel.style.display === 'block') {
            notificationsPanel.style.display = 'none';
        } else {
            notificationsPanel.style.display = 'block';
        }
    });

    // Close notifications panel when close button is clicked
    closeButton.addEventListener('click', function () {
        notificationsPanel.style.display = 'none';
    });

    // Close notifications panel when clicking outside
    document.addEventListener('click', function (e) {
        if (notificationsPanel.style.display === 'block' &&
            !notificationsPanel.contains(e.target) &&
            e.target !== bellIcon) {
            notificationsPanel.style.display = 'none';
        }
    });

    // Switch between tabs
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', function () {
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
        });
    });

    const seeMoreLink = document.querySelector('.see-more');
    const additionalTopics = document.querySelectorAll('.additional-topic');

    seeMoreLink.addEventListener('click', function (e) {
        e.preventDefault();
        additionalTopics.forEach(topic => {
            if (topic.style.display === 'none' || topic.style.display === '') {
                topic.style.display = 'inline-block';
                seeMoreLink.textContent = 'See less';
            } else {
                topic.style.display = 'none';
                seeMoreLink.textContent = 'See more';
            }
        });
    });

    const profileIcon = document.querySelector('.profile-icon');
    const profileDropdown = document.getElementById('profileDropdown');

    // Toggle profile dropdown when profile icon is clicked
    profileIcon.addEventListener('click', function (e) {
        e.stopPropagation();
        if (profileDropdown.style.display === 'block') {
            profileDropdown.style.display = 'none';
        } else {
            profileDropdown.style.display = 'block';
            notificationsPanel.style.display = 'none'; // Close notifications if open
        }
    });

    // Close profile dropdown when clicking outside
    document.addEventListener('click', function (e) {
        if (profileDropdown.style.display === 'block' &&
            !profileDropdown.contains(e.target) &&
            e.target !== profileIcon) {
            profileDropdown.style.display = 'none';
        }
    });

    // Handle three-dots dropdown
    document.querySelectorAll('.bi-three-dots').forEach(icon => {
        icon.addEventListener('click', function (e) {
            e.stopPropagation();
            const dropdown = this.closest('.article-actions').querySelector('.article-options-dropdown');

            // Close all other dropdowns first
            document.querySelectorAll('.article-options-dropdown').forEach(d => {
                if (d !== dropdown) d.style.display = 'none';
            });

            // Toggle current dropdown
            dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
        });
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', function (e) {
        if (!e.target.closest('.article-actions')) {
            document.querySelectorAll('.article-options-dropdown').forEach(d => {
                d.style.display = 'none';
            });
        }
    });

    // Navigation tabs scrolling functionality
    const tabsContainer = document.querySelector('.nav-tabs');
    const leftButton = document.querySelector('.scroll-button.left');
    const rightButton = document.querySelector('.scroll-button.right');

    function updateScrollButtons() {
        const isScrollable = tabsContainer.scrollWidth > tabsContainer.clientWidth;
        const isAtStart = tabsContainer.scrollLeft <= 0;
        const isAtEnd = tabsContainer.scrollLeft >= (tabsContainer.scrollWidth - tabsContainer.clientWidth);

        leftButton.classList.toggle('hidden', isAtStart || !isScrollable);
        rightButton.classList.toggle('hidden', isAtEnd || !isScrollable);
    }

    function scrollTabs(direction) {
        const scrollAmount = tabsContainer.clientWidth / 2;
        tabsContainer.scrollBy({
            left: direction === 'left' ? -scrollAmount : scrollAmount,
            behavior: 'smooth'
        });
    }

    leftButton.addEventListener('click', () => scrollTabs('left'));
    rightButton.addEventListener('click', () => scrollTabs('right'));

    // Update buttons on scroll
    tabsContainer.addEventListener('scroll', updateScrollButtons);

    // Update buttons on resize
    window.addEventListener('resize', updateScrollButtons);

    // Initial check
    updateScrollButtons();

    // Make tabs clickable
    const navButtons = tabsContainer.querySelectorAll('button:not(.icon-btn)');
    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
        });
    });

    // Author card follow button functionality
    document.querySelectorAll('.author-card-follow').forEach(button => {
        button.addEventListener('click', (e) => {
            e.stopPropagation();
            button.classList.toggle('following');
            button.textContent = button.classList.contains('following') ? 'Following' : 'Follow';
        });
    });

    // Scroll to top functionality
    const scrollToTopButton = document.querySelector('.scroll-to-top');

    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            scrollToTopButton.classList.add('show');
        } else {
            scrollToTopButton.classList.remove('show');
        }
    });

    scrollToTopButton.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
});