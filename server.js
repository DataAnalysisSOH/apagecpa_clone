const express = require('express');
const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');

const app = express();
const PORT = 3000;

// Serve static files
app.use(express.static('.'));

// AJAX endpoint to load more posts
app.get('/load-more-posts', (req, res) => {
    const page = parseInt(req.query.page) || 1;
    
    // Try different possible file paths
    let filePath;
    let html;
    
    // Option 1: tax-news/3.html
    filePath = path.join(__dirname, 'tax-news', `${page}.html`);
    
    if (!fs.existsSync(filePath)) {
        // Option 2: tax-news/3/index.html
        filePath = path.join(__dirname, 'tax-news', page.toString(), 'index.html');
    }
    
    console.log(`Loading page ${page} from: ${filePath}`);
    
    if (!fs.existsSync(filePath)) {
        console.log('File not found');
        return res.status(404).json({ error: 'Page not found' });
    }
    
    try {
        html = fs.readFileSync(filePath, 'utf8');
        const $ = cheerio.load(html);
        
        // Extract only the post articles
        const posts = [];
        $('.elementor-post').each((i, elem) => {
            posts.push($.html(elem));
        });
        
        console.log(`Found ${posts.length} posts`);
        
        const nextPage = page + 1;
        
        // Check both possible paths for next page
        let nextFilePath = path.join(__dirname, 'tax-news', `${nextPage}.html`);
        if (!fs.existsSync(nextFilePath)) {
            nextFilePath = path.join(__dirname, 'tax-news', nextPage.toString(), 'index.html');
        }
        const hasMore = fs.existsSync(nextFilePath);
        
        res.json({
            success: true,
            posts: posts,
            nextPage: nextPage,
            hasMore: hasMore
        });
    } catch (error) {
        console.error('Error:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

app.listen(PORT, () => {
    console.log(`✅ Server running at http://localhost:3000`);
    console.log(`📄 Open: http://localhost:3000/tax-news/2.html`);
});