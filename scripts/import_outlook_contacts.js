// 尝试使用 Microsoft Graph API 导入联系人到 Outlook
const https = require('https');
const fs = require('fs');

const contacts = [
  { name: '冯俊锋', company: '广东百事泰医疗器械股份有限公司', phone: '15986835975', email: 'fengjunfeng@bestek.com' },
  { name: '龙荣深', company: '广州橙行智动汽车科技有限公司', phone: '18613008542', email: '' },
  { name: '王军', company: '深圳市华宝新能股份有限公司', phone: '13714216395', email: 'wangj@hello-tech.com' },
  { name: '石晓峰', company: '深圳市云之梦科技有限公司', phone: '15919839103', email: 'shixf@cloudream.com' },
  { name: '郭荣威', company: '生益电子股份有限公司', phone: '13412014700', email: 'david.guo@sye.com.cn' },
  { name: '陈虹伊', company: '广州导远电子科技有限公司', phone: '18658683298', email: 'chenhongyi@asensing.com' },
  { name: '陈子兴', company: '广州黑格智造信息科技有限公司', phone: '13828417724', email: '48228062@qq.com' },
  { name: '黄举荣', company: '佳都科技集团股份有限公司', phone: '13710100606', email: 'huang_jurong@163.com' },
  { name: '雷杰', company: '广芯微电子（广州）股份有限公司', phone: '13427516261', email: 'jerry.lei@unicmicro.com' },
  { name: '苏立强', company: '康佳集团股份有限公司', phone: '13510283328', email: 'suliqiang@konka.com' },
  { name: '刘舟', company: '深圳鎏信科技有限公司', phone: '', email: '' },
  { name: '柯栋', company: '珠海格力集团有限公司', phone: '18575606188', email: '' },
  { name: '李绍斌', company: '珠海格力集团有限公司', phone: '18666997633', email: '' },
  { name: '彭才能', company: '珠海格力集团有限公司', phone: '13923369286', email: '13923369286@139.com' },
  { name: '艾国华', company: '广东博力威科技股份有限公司', phone: '13790445863', email: '532201345@qq.com' },
  { name: '朱伟', company: '东风日产乘用车公司', phone: '15827328512', email: 'dpliujun@dfl.com.cn' },
  { name: 'Vincent Liu', company: '东风日产乘用车公司', phone: '15994291519', email: 'dpliujun@dfl.com.cn' },
  { name: '李子坚', company: '海能达通信股份有限公司', phone: '13922870074', email: '' },
  { name: '李平', company: '中邮消费金融有限公司', phone: '15626097529', email: '' },
  { name: '蔡工', company: '中邮消费金融有限公司', phone: '17724240350', email: 'caijm@gcbidding.com' },
  { name: '贾奎', company: '跨维（深圳）智能数字科技有限公司', phone: '13808823105', email: 'jiakui@dexforce.com' },
  { name: '吴迪', company: '跨维（深圳）智能数字科技有限公司', phone: '', email: '' },
  { name: '余文', company: '深圳市汇川技术股份有限公司', phone: '13480207613', email: '2261929453@qq.com' },
  { name: '黄冠', company: '深圳十方融海科技有限公司', phone: '', email: '' },
  { name: '张峻彬', company: '云鲸智能创新（深圳）有限公司', phone: '', email: '' },
  { name: '许晋诚', company: '帕西尼感知科技（深圳）有限公司', phone: '', email: '' },
  { name: '赵同阳', company: '深圳市众擎机器人科技有限公司', phone: '', email: '' },
  { name: '董典彪', company: '深圳赛博格机器人有限公司', phone: '', email: '' },
  { name: '郑随兵', company: '睿尔曼智能科技（深圳）有限公司', phone: '', email: '' },
  { name: '陈小森', company: '乐森机器人（深圳）有限公司', phone: '', email: '' },
  { name: '刘培超', company: '深圳市越疆科技股份有限公司', phone: '', email: '' },
  { name: '徐方怡', company: '追觅科技（深圳）有限公司', phone: '', email: '' },
  { name: '杨洪', company: '深圳市航盛电子股份有限公司', phone: '', email: '' },
  { name: '刘程宇', company: '深圳科士达科技股份有限公司', phone: '', email: '' },
  { name: '周伟', company: '深圳乐动机器人有限公司', phone: '', email: '' },
  { name: '林中山', company: '深圳市塞防科技有限公司', phone: '', email: '' },
];

// 生成vCard
function toVCard(contact) {
  const lines = [
    'BEGIN:VCARD',
    'VERSION:3.0',
    `FN:${contact.name || ''}`,
    `N:${contact.name || ''};;;`
  ];
  if (contact.company) lines.push(`ORG:${contact.company}`);
  if (contact.phone) lines.push(`TEL;TYPE=CELL:${contact.phone}`);
  if (contact.email) lines.push(`EMAIL:${contact.email}`);
  lines.push('END:VCARD');
  return lines.join('\r\n');
}

const vCards = contacts.map(c => toVCard(c)).join('\r\n');
fs.writeFileSync('/root/.openclaw/workspace/Outlook_contacts_import.vcf', vCards);
console.log(`生成了 ${contacts.length} 个联系人vCard`);
console.log('文件：/root/.openclaw/workspace/Outlook_contacts_import.vcf');
