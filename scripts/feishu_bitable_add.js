#!/usr/bin/env node
// Node.js 22+ has native fetch

const FEISHU_APP_ID = 'cli_a94ca893af789bd3';
const FEISHU_APP_SECRET = 'qRafcJHfVEDNOZQOywkQwb6wtnOVRA0y';
const APP_TOKEN = 'BO6kb2c7haHY2FsLJCecH1mrnhe';
const TABLE_ID = 'tblDEBAW1NOq61Ch';

async function getTenantAccessToken() {
    const url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal';
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_id: FEISHU_APP_ID, app_secret: FEISHU_APP_SECRET })
    });
    const data = await res.json();
    if (data.code !== 0) throw new Error(`Auth Failed: ${data.msg}`);
    return data.tenant_access_token;
}

async function listFields(appToken, token, tableId) {
    const url = `https://open.feishu.cn/open-apis/bitable/v1/apps/${appToken}/tables/${tableId}/fields`;
    const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    if (data.code !== 0) throw new Error(`List Fields Failed: ${data.msg}`);
    return data.data.items;
}

async function addRecord(appToken, token, tableId, fields) {
    const url = `https://open.feishu.cn/open-apis/bitable/v1/apps/${appToken}/tables/${tableId}/records`;
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ fields })
    });
    const data = await res.json();
    console.log('Add Record Response:', JSON.stringify(data, null, 2));
    if (data.code !== 0) throw new Error(`Add Record Failed: ${data.msg}`);
    return data.data.record;
}

async function main() {
    const companyName = process.argv[2] || '深圳市普渡科技股份有限公司';
    const content = process.argv[3] || '';

    console.log('🔑 Getting access token...');
    const token = await getTenantAccessToken();
    console.log('✅ Token obtained\n');

    console.log('📋 Listing fields...');
    const fields = await listFields(APP_TOKEN, token, TABLE_ID);
    console.log('Available fields:');
    fields.forEach(f => console.log(`  - ${f.field_name} (${f.type})`));
    console.log('');

    const record = {
        'Customer': companyName,
        '企业信息收集': content
    };

    console.log('➕ Adding record...');
    const result = await addRecord(APP_TOKEN, token, TABLE_ID, record);
    console.log('✅ Record added! ID:', result.record_id);
}

main().catch(e => { console.error('❌ Error:', e.message); process.exit(1); });
