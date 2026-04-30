// Fix Load More button for static HTML site
(function() {
    'use strict';
    
    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        
        // Find the load more button
        const loadMoreButton = document.querySelector('.elementor-button');
        const loadMoreAnchor = document.querySelector('.e-load-more-anchor');
        const postsContainer = document.querySelector('.elementor-posts-container');
        const spinner = document.querySelector('.e-load-more-spinner');
        
        if (!loadMoreButton || !loadMoreAnchor || !postsContainer) {
            console.log('Load more elements not found');
            return;
        }
        
        // Get pagination data
        let currentPage = parseInt(loadMoreAnchor.getAttribute('data-page')) || 1;
        const maxPage = parseInt(loadMoreAnchor.getAttribute('data-max-page')) || 1;
        
        // Function to load next page
        function loadNextPage() {
            const nextPage = currentPage + 1;
            
            if (nextPage > maxPage) {
                loadMoreButton.style.display = 'none';
                return;
            }
            
            // Show spinner
            if (spinner) {
                spinner.style.display = 'inline-block';
            }
            loadMoreButton.style.opacity = '0.5';
            loadMoreButton.style.pointerEvents = 'none';
            
            // Construct the URL for the next page
            let nextPageUrl;
            if (currentPage === 1) {
                // From page 1 to page 2
                nextPageUrl = '2.html';
            } else {
                // From page N to page N+1
                nextPageUrl = `${nextPage}.html`;
            }
            
            // Fetch the next page
            fetch(nextPageUrl)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Page not found');
                    }
                    return response.text();
                })
                .then(html => {
                    // Parse the HTML
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    
                    // Extract the posts from the loaded page
                    const newPosts = doc.querySelectorAll('.elementor-post');
                    
                    if (newPosts.length === 0) {
                        throw new Error('No posts found');
                    }
                    
                    // Append new posts to the container
                    newPosts.forEach(post => {
                        postsContainer.appendChild(post.cloneNode(true));
                    });
                    
                    // Update current page
                    currentPage = nextPage;
                    loadMoreAnchor.setAttribute('data-page', currentPage);
                    
                    // Update next page URL
                    const nextNextPage = currentPage + 1;
                    if (nextNextPage <= maxPage) {
                        loadMoreAnchor.setAttribute('data-next-page', `${nextNextPage}.html`);
                    }
                    
                    // Hide spinner
                    if (spinner) {
                        spinner.style.display = 'none';
                    }
                    loadMoreButton.style.opacity = '1';
                    loadMoreButton.style.pointerEvents = 'auto';
                    
                    // Hide button if we've reached the last page
                    if (currentPage >= maxPage) {
                        loadMoreButton.style.display = 'none';
                    }
                    
                    console.log(`Loaded page ${currentPage} of ${maxPage}`);
                })
                .catch(error => {
                    console.error('Error loading page:', error);
                    
                    // Hide spinner
                    if (spinner) {
                        spinner.style.display = 'none';
                    }
                    
                    // Show error message
                    const errorMsg = document.querySelector('.e-load-more-message');
                    if (errorMsg) {
                        errorMsg.textContent = 'Error loading more posts. Please try again.';
                        errorMsg.style.display = 'block';
                    }
                    
                    loadMoreButton.style.opacity = '1';
                    loadMoreButton.style.pointerEvents = 'auto';
                });
        }
        
        // Add click event listener to the button
        loadMoreButton.addEventListener('click', function(e) {
            e.preventDefault();
            loadNextPage();
        });
        
        // Hide button if already on last page
        if (currentPage >= maxPage) {
            loadMoreButton.style.display = 'none';
        }
    });
})();