#!/usr/bin/env node
// 批量检查公司是否已存在于飞书多维表格

const FEISHU_APP_ID = 'cli_a94ca893af789bd3';
const FEISHU_APP_SECRET = 'qRafcJHfVEDNOZQOywkQwb6wtnOVRA0y';
const APP_TOKEN = 'BO6kb2c7haHY2FsLJCecH1mrnhe';
const TABLE_ID = 'tblDEBAW1NOq61Ch';

const COMPANIES = [
  "深圳市道通智能航空技术股份有限公司",
  "惠州市华阳多媒体电子有限公司",
  "深圳市佰维存储科技股份有限公司",
  "深圳市塞防科技有限公司",
  "深圳乐动机器人有限公司",
  "深圳科士达科技股份有限公司",
  "深圳市航盛电子股份有限公司",
  "追觅科技（深圳）有限公司",
  "深圳市越疆科技股份有限公司",
  "广东博力威科技股份有限公司",
  "广东新宝电器有限公司",
  "广州极飞科技股份有限公司",
  "佳都科技集团股份有限公司",
  "乐森机器人（深圳）有限公司",
  "诺亚舟教育科技（深圳）有限公司",
  "帕西尼感知科技（深圳）有限公司",
  "睿尔曼智能科技（深圳）有限公司",
  "深圳赛博格机器人有限公司",
  "深圳市华宝新能股份有限公司",
  "深圳市众擎机器人科技有限公司",
  "生益电子股份有限公司",
  "云鲸智能创新（深圳）有限公司",
  "合创汽车科技有限公司",
  "大统营科技（惠州）有限公司",
  "丰图科技（深圳）有限公司",
  "深圳十方融海科技有限公司",
  "广东朗科智能电气有限公司",
  "中邮消费金融有限公司",
  "深圳市卓驭科技有限公司",
  "安克创新科技股份有限公司",
  "跨维（深圳）智能数字科技有限公司",
  "深圳市普渡科技股份有限公司",
  "深圳鎏信科技有限公司"
];

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

async function getAllRecords(token) {
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
        console.log(`Fetched ${allRecords.length} records...`);
    }

    return allRecords;
}

async function main() {
    console.log('🔑 Getting access token...');
    const token = await getTenantAccessToken();
    console.log('✅ Token obtained\n');

    console.log('📋 Fetching all records from Feishu table...');
    const allRecords = await getAllRecords(token);
    console.log(`Total records in table: ${allRecords.length}\n`);

    const existingCustomers = new Set(allRecords.map(r => r.fields.Customer).filter(Boolean));

    console.log('=' .repeat(60));
    console.log('📊 检查结果');
    console.log('=' .repeat(60));

    const toAdd = [];
    const alreadyExist = [];

    for (const company of COMPANIES) {
        if (existingCustomers.has(company)) {
            alreadyExist.push(company);
            console.log(`✅ 已存在: ${company}`);
        } else {
            toAdd.push(company);
            console.log(`❌ 需要添加: ${company}`);
        }
    }

    console.log('\n' + '=' .repeat(60));
    console.log(`📝 统计结果: 共 ${COMPANIES.length} 家公司`);
    console.log(`✅ 已存在: ${alreadyExist.length} 家`);
    console.log(`❌ 需要添加: ${toAdd.length} 家`);
    console.log('=' .repeat(60));

    if (toAdd.length > 0) {
        console.log('\n📋 需要添加的公司列表:');
        toAdd.forEach((c, i) => console.log(`  ${i+1}. ${c}`));
    }

    // Output as JSON for further processing
    console.log('\n--- JSON OUTPUT ---');
    console.log(JSON.stringify({ toAdd, alreadyExist }, null, 2));
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
