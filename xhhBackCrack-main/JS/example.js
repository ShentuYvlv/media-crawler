const { generateRequestUrl, listRoutes, ROUTES } = require('./Hkey.js');

// 使用示例

console.log('='.repeat(60));
console.log('小黑盒 API 请求链接生成器');
console.log('='.repeat(60));

// 1. 列出所有可用路由
listRoutes();

// 2. 生成指定路由的请求链接
console.log('\n\n生成请求链接示例:');
console.log('='.repeat(60));

// 示例1: 生成表情列表API的请求链接
try {
    const result1 = generateRequestUrl('emojis_list');
    console.log('\n[1] 表情列表 API:');
    console.log(`路径: ${result1.path}`);
    console.log(`hkey: ${result1.hkey}`);
    console.log(`时间戳: ${result1.timestamp}`);
    console.log(`nonce: ${result1.nonce}`);
    console.log(`完整URL:\n${result1.url}`);
} catch (error) {
    console.error('错误:', error.message);
}

// 示例2: 生成数据上报API的请求链接
try {
    const result2 = generateRequestUrl('data_report');
    console.log('\n[2] 数据上报 API:');
    console.log(`路径: ${result2.path}`);
    console.log(`hkey: ${result2.hkey}`);
    console.log(`完整URL:\n${result2.url}`);
} catch (error) {
    console.error('错误:', error.message);
}

// 示例3: 生成话题分类API的请求链接
try {
    const result3 = generateRequestUrl('topic_categories');
    console.log('\n[3] 话题分类 API:');
    console.log(`路径: ${result3.path}`);
    console.log(`hkey: ${result3.hkey}`);
    console.log(`完整URL:\n${result3.url}`);
} catch (error) {
    console.error('错误:', error.message);
}

// 示例4: 生成搜索发现API的请求链接
try {
    const result4 = generateRequestUrl('search_found');
    console.log('\n[4] 搜索发现 API:');
    console.log(`路径: ${result4.path}`);
    console.log(`hkey: ${result4.hkey}`);
    console.log(`完整URL:\n${result4.url}`);
} catch (error) {
    console.error('错误:', error.message);
}

// 示例5: 生成动态流API的请求链接（带自定义参数）
try {
    const result5 = generateRequestUrl('feeds', { offset: '10', dw: '1024' });
    console.log('\n[5] 动态流 API (自定义参数):');
    console.log(`路径: ${result5.path}`);
    console.log(`hkey: ${result5.hkey}`);
    console.log(`完整URL:\n${result5.url}`);
} catch (error) {
    console.error('错误:', error.message);
}

console.log('\n' + '='.repeat(60));
