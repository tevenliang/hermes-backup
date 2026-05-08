#!/usr/bin/env node
const { execSync } = require('child_process');

// Get cookies from file
const fs = require('fs');
const cookies = JSON.parse(fs.readFileSync('/root/.openclaw/scripts/xhs_cookies.json', 'utf8'));
const cookieStr = cookies.map(c => `${c.name}=${c.value}`).join('; ');

const proxy = 'http://60.215.152.136:20170';
const keyword = 'openclaw';

console.log('Using proxy:', proxy);
console.log('Cookies:', cookieStr.split(';').slice(0,3).join(';') + '...');

// Try to fetch search page via proxy with cookies
try {
  const curl = `curl -s --proxy "${proxy}" \\
    -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \\
    -H "Cookie: ${cookieStr}" \\
    -H "Referer: https://www.xiaohongshu.com/" \\
    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \\
    -H "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8" \\
    -L "https://www.xiaohongshu.com/search_result?keyword=${encodeURIComponent(keyword)}&source=web_explore_feed" \\
    -o /tmp/xhs_search_result.html \\
    -w "HTTP %{http_code}" \\
    --connect-timeout 15`;

  const result = execSync(curl, { encoding: 'utf8' });
  console.log('Result:', result);

  const html = fs.readFileSync('/tmp/xhs_search_result.html', 'utf8');
  console.log('HTML size:', html.length);

  // Extract text content
  const textMatch = html.match(/"noteCards":\[(.*?)\]/s);
  if (textMatch) {
    console.log('Found noteCards:', textMatch[1].substring(0, 500));
  }

  // Look for any text content
  const plainText = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  const openclawMatches = plainText.match(/.{0,50}[Oo]pen[Cc]law.{0,100}/g);
  if (openclawMatches) {
    console.log('\nOpenClaw mentions:');
    openclawMatches.slice(0, 10).forEach(m => console.log(' -', m.trim()));
  } else {
    console.log('\nNo OpenClaw mentions found in page');
    // Try to find what's in the page
    const titleMatch = html.match(/<title>(.*?)<\/title>/i);
    console.log('Page title:', titleMatch ? titleMatch[1] : 'not found');
  }

} catch (e) {
  console.error('Error:', e.message);
}
