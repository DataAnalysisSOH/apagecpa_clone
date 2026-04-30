document.addEventListener('DOMContentLoaded', function() {
    console.log('Custom load more script loaded');
    
    const loadMoreBtn = document.querySelector('.e-load-more-anchor + .elementor-button-wrapper .elementor-button');
    const postsContainer = document.querySelector('.elementor-posts-container');
    const loadMoreAnchor = document.querySelector('.e-load-more-anchor');
    const spinner = document.querySelector('.e-load-more-spinner');
    
    if (!loadMoreBtn) {
        console.log('Load more button not found');
        return;
    }
    
    if (!postsContainer) {
        console.log('Posts container not found');
        return;
    }
    
    console.log('Load more button found, adding click handler');
    
    let currentPage = parseInt(loadMoreAnchor.getAttribute('data-page')) || 2;
    const maxPage = parseInt(loadMoreAnchor.getAttribute('data-max-page')) || 12;
    let isLoading = false;
    
    loadMoreBtn.addEventListener('click', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        console.log(`Load more clicked. Current page: ${currentPage}, Max page: ${maxPage}`);
        
        if (isLoading) {
            console.log('Already loading...');
            return;
        }
        
        if (currentPage >= maxPage) {
            console.log('Reached max page');
            return;
        }
        
        isLoading = true;
        loadMoreBtn.style.opacity = '0.5';
        if (spinner) spinner.style.display = 'inline-block';
        
        try {
            const nextPage = currentPage + 1;
            const url = `/.netlify/functions/load-more-posts?page=${nextPage}`;
            console.log(`Fetching: ${url}`);
            
            const response = await fetch(url);
            const data = await response.json();
            
            console.log('Response:', data);
            
            if (data.success && data.posts && data.posts.length > 0) {
                console.log(`Adding ${data.posts.length} posts`);
                
                // Add new posts to the container
                data.posts.forEach(postHtml => {
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = postHtml;
                    const article = tempDiv.firstElementChild;
                    postsContainer.appendChild(article);
                });
                
                currentPage = nextPage;
                loadMoreAnchor.setAttribute('data-page', currentPage);
                
                console.log(`Updated to page ${currentPage}`);
                
                // Hide button if no more posts
                if (!data.hasMore || currentPage >= maxPage) {
                    console.log('No more posts, hiding button');
                    loadMoreBtn.parentElement.style.display = 'none';
                }
            } else {
                console.log('No posts in response');
            }
        } catch (error) {
            console.error('Error loading more posts:', error);
            alert('Failed to load more posts. Please check the console.');
        } finally {
            isLoading = false;
            loadMoreBtn.style.opacity = '1';
            if (spinner) spinner.style.display = 'none';
        }
    });
});