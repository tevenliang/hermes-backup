const https = require('https');

// 读取飞书表格记录
async function getFeishuRecords() {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'open.feishu.cn',
      path: '/open-apis/bitable/v1/apps/BO6kb2c7haHY2FsLJCecH1mrnhe/tables/tblDEBAW1NOq61Ch/records?page_size=500',
      method: 'GET',
      headers: {
        'Authorization': 'Bearer t-g1043seFMMS2PNKQNX6QFHDRZKXSVBNAQSPQJTVI',
        'Content-Type': 'application/json'
      }
    };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', d => data += d);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          resolve(json.data.items);
        } catch(e) {
          reject(e);
        }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

// 解析联系人字符串，提取姓名、电话、邮箱
function parseContacts(contactStr, companyName) {
  if (!contactStr || contactStr === 'null' || contactStr.trim() === '') return [];
  
  const contacts = [];
  // 按换行分割，可能有多个联系人
  const lines = contactStr.split('\n').filter(l => l.trim());
  
  let currentContact = null;
  
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    
    // 检测是否是分隔线
    if (trimmed.startsWith('---')) {
      if (currentContact && currentContact.name) {
        contacts.push(currentContact);
      }
      currentContact = { company: companyName };
      continue;
    }
    
    // 初始化联系人
    if (!currentContact) currentContact = { company: companyName };
    
    // 提取电话（多种格式）
    const phoneMatch = trimmed.match(/(?:电话|Mobile|手机|电话:)\s*[:：]?\s*([0-9\-]+)|([0-9]{11,})/);
    if (phoneMatch) {
      const phone = (phoneMatch[1] || phoneMatch[2]).replace(/-/g, '');
      if (phone.length >= 7 && !currentContact.phone) {
        currentContact.phone = phone;
        continue;
      }
    }
    
    // 提取邮箱
    const emailMatch = trimmed.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/i);
    if (emailMatch) {
      if (!currentContact.email) currentContact.email = emailMatch[1].toLowerCase();
      continue;
    }
    
    // 提取姓名（通常是第一个没有被识别为电话/邮箱的长字符串）
    if (!currentContact.name && trimmed.length >= 2 && trimmed.length <= 30 && !phoneMatch && !emailMatch) {
      // 过滤掉职位描述
      if (!trimmed.includes('经理') || !trimmed.includes('http')) {
        currentContact.name = trimmed.replace(/[，。；;]/g, '').trim();
      }
    }
  }
  
  if (currentContact && currentContact.name) {
    contacts.push(currentContact);
  }
  
  return contacts;
}

// 生成vCard格式
function toVCard(contact) {
  const lines = [
    'BEGIN:VCARD',
    'VERSION:3.0',
    `FN:${contact.name || ''}`
  ];
  
  if (contact.company) lines.push(`ORG:${contact.company}`);
  if (contact.phone) lines.push(`TEL;TYPE=CELL:${contact.phone}`);
  if (contact.email) lines.push(`EMAIL:${contact.email}`);
  
  lines.push('END:VCARD');
  return lines.join('\r\n');
}

async function main() {
  console.log('正在读取飞书表格记录...');
  const records = await getFeishuRecords();
  console.log(`共 ${records.length} 条记录`);
  
  const allContacts = [];
  
  for (const record of records) {
    const customerName = record.fields.Customer || '';
    const contactsStr = record.fields.Contacts;
    
    if (contactsStr) {
      const parsed = parseContacts(contactsStr, customerName);
      allContacts.push(...parsed);
    }
  }
  
  console.log(`共解析出 ${allContacts.length} 个联系人`);
  
  // 生成vCard文件
  const vCards = allContacts.map(c => toVCard(c)).join('\r\n');
  require('fs').writeFileSync('/root/.openclaw/workspace/contacts_from_feishu.vcf', vCards);
  console.log('已保存到 /root/.openclaw/workspace/contacts_from_feishu.vcf');
  
  // 也输出CSV方便查看
  const csv = ['姓名,公司,电话,邮箱'];
  for (const c of allContacts) {
    csv.push(`"${(c.name||'').replace(/"/g,'""')}","${(c.company||'').replace(/"/g,'""')}","${c.phone||''}","${c.email||''}"`);
  }
  require('fs').writeFileSync('/root/.openclaw/workspace/contacts_from_feishu.csv', csv.join('\n'));
  console.log('已保存到 /root/.openclaw/workspace/contacts_from_feishu.csv');
  
  // 打印前20个联系人
  console.log('\n前20个联系人预览：');
  allContacts.slice(0, 20).forEach((c, i) => {
    console.log(`${i+1}. ${c.name} | ${c.company} | ${c.phone || '-'} | ${c.email || '-'}`);
  });
}

main().catch(console.error);
