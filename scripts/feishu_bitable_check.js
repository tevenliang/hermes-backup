#!/usr/bin/env node
// 检查公司是否已存在于飞书多维表格

const FEISHU_APP_ID = 'cli_a94ca893af789bd3';
const FEISHU_APP_SECRET = 'qRafcJHfVEDNOZQOywkQwb6wtnOVRA0y';
const APP_TOKEN = 'BO6kb2c7haHY2FsLJCecH1mrnhe';
const TABLE_ID = 'tblDEBAW1NOq61Ch';

async function getTenantAccessToken() {
    const res = await fetch('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_id: FEISHU_APP_ID, app_secret: FEISHU_APP_SECRET })
    });
    const data = await res.json();
    if (data.code !== 0) throw new Error(`Auth Failed: ${data.msg}`);
    return data.tenant_access_token;
}

async function searchRecords(token, companyName) {
    const url = `https://open.feishu.cn/open-apis/bitable/v1/apps/${APP_TOKEN}/tables/${TABLE_ID}/records?filter=CurrentValue["Customer"]="${companyName}"&page_size=5`;
    const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    if (data.code !== 0) {
        // 如果过滤查询不支持，尝试获取所有记录
        console.log('Filter not supported, fetching all records...');
        return searchRecordsAll(token, companyName);
    }
    return data.data;
}

async function searchRecordsAll(token, companyName) {
    let hasMore = true;
    let pageToken = '';
    const allRecords = [];

    while (hasMore) {
        let url = `https://open.feishu.cn/open-apis/bitable/v1/apps/${APP_TOKEN}/tables/${TABLE_ID}/records?page_size=100`;
        if (pageToken) url += `&page_token=${pageToken}`;

        const res = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        if (data.code !== 0) throw new Error(`Query Failed: ${data.msg}`);

        allRecords.push(...data.data.items);
        hasMore = data.data.has_more;
        pageToken = data.data.page_token;
    }

    // 在内存中搜索
    const found = allRecords.find(r => r.fields.Customer === companyName);
    return found ? { items: [found], total: 1 } : { items: [], total: 0 };
}

async function main() {
    const companyName = process.argv[2] || '';

    if (!companyName) {
        console.log('Usage: node feishu_bitable_check.js "[公司名称]"');
        process.exit(1);
    }

    console.log(`🔍 Checking if "${companyName}" exists in Feishu table...`);
    const token = await getTenantAccessToken();

    try {
        const result = await searchRecords(token, companyName);
        if (result.items && result.items.length > 0) {
            const record = result.items[0];
            console.log(JSON.stringify({
                exists: true,
                record_id: record.record_id,
                fields: record.fields
            }));
        } else {
            console.log(JSON.stringify({ exists: false, record_id: null }));
        }
    } catch (e) {
        console.error('Error:', e.message);
        console.log(JSON.stringify({ exists: false, error: e.message }));
    }
}

main();
